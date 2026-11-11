"""Canal de importación de un PDF (reanudable por documento)."""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.providers import LLMProvider, LLMUnavailable
from app.document_processing.chunking import build_pieces
from app.document_processing.classify import classify, discoveries
from app.document_processing.extract import extract
from app.engines.rules.abilities import SKILLS
from app.models import Campaign, Document, DocumentAsset, DocumentChunk, Fact, Scene
from app.services.events import append_event

log = logging.getLogger("vdm.pdf")
MAP_WORDS = ("mapa", "map", "plano", "planta", "nivel", "level", "dungeon", "mazmorra")


def campaign_dir(data_dir: Path, campaign_id: str) -> Path:
    return data_dir / "campaigns" / campaign_id


def register_upload(db: Session, campaign: Campaign, data_dir: Path, filename: str, source: Path,
                    title: str | None = None) -> Document:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    existing = db.scalar(select(Document).where(Document.campaign_id == campaign.id, Document.sha256 == digest))
    if existing:
        return existing
    target_dir = campaign_dir(data_dir, campaign.id) / "documents"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{digest[:16]}.pdf"
    shutil.copyfile(source, target)
    document = Document(campaign_id=campaign.id, title=title or Path(filename).stem, filename=filename,
                        file_path=str(target), sha256=digest, status="pending", log=[])
    db.add(document)
    db.flush()
    append_event(db, campaign.id, "document_uploaded", {"document_id": document.id, "title": document.title},
                 visibility="dm")
    return document


def _progress(db: Session, document: Document, value: int, message: str) -> None:
    document.progress = value
    document.log = [*document.log, message]
    db.commit()


def process_document(db: Session, document: Document, data_dir: Path, provider: LLMProvider | None) -> None:
    try:
        _process(db, document, data_dir, provider)
    except Exception as exc:
        db.rollback()
        document.status = "error"
        document.log = [*document.log, f"Error: {exc}"]
        db.commit()
        log.exception("Error procesando %s", document.filename)
        raise


def _process(db: Session, document: Document, data_dir: Path, provider: LLMProvider | None) -> None:
    document.status = "processing"
    document.log = []
    # Reprocesar desde cero: se borran fragmentos e imágenes anteriores de este documento.
    old_chunks = select(DocumentChunk.id).where(DocumentChunk.document_id == document.id)
    db.execute(delete(Fact).where(Fact.source == "pdf", Fact.source_chunk_id.in_(old_chunks)))
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    db.execute(delete(DocumentAsset).where(DocumentAsset.document_id == document.id))
    _progress(db, document, 5, "Leyendo el PDF…")

    assets_dir = campaign_dir(data_dir, document.campaign_id) / "assets" / document.id
    extraction = extract(Path(document.file_path), assets_dir)
    document.page_count = extraction.page_count
    for warning in extraction.warnings:
        document.log = [*document.log, warning]
    _progress(db, document, 40, f"{extraction.page_count} páginas, {len(extraction.blocks)} bloques de texto, "
                                f"{len(extraction.images)} imágenes, {len(extraction.tables)} tablas.")

    pieces = build_pieces(extraction.blocks, extraction.body_size)
    scenes: dict[str, Scene] = {}
    order = len(list(db.scalars(select(Scene.id).where(Scene.campaign_id == document.campaign_id))))
    chunks: list[DocumentChunk] = []
    facts = 0
    for ordinal, piece in enumerate(pieces):
        result = classify(piece.text, read_aloud=piece.read_aloud)
        scene = None
        if piece.area:
            scene = scenes.get(piece.area)
            if scene is None:
                scene = Scene(campaign_id=document.campaign_id, name=piece.area[:200], order_index=order)
                order += 1
                db.add(scene)
                db.flush()
                scenes[piece.area] = scene
            if result.kind == "read_aloud" and not scene.summary_public:
                scene.summary_public = piece.text[:2000]
            elif result.kind == "narrative" and not scene.summary_dm:
                scene.summary_dm = piece.text[:2000]
        chunk = DocumentChunk(
            document_id=document.id, campaign_id=document.campaign_id, ordinal=ordinal,
            page_start=piece.page_start, page_end=piece.page_end, section=piece.section[:400], kind=result.kind,
            text=piece.text, knowledge_level=result.level, classification_reason=result.reason,
            scene_id=scene.id if scene else None,
        )
        db.add(chunk)
        db.flush()
        chunks.append(chunk)
        for found in discoveries(piece.text):
            db.add(Fact(campaign_id=document.campaign_id, scene_id=scene.id if scene else None,
                        subject=piece.area or piece.section[:200], statement=found.sentence,
                        knowledge_level="conditional", source="pdf", source_chunk_id=chunk.id,
                        discovery={"skill": found.skill, "dc": found.dc} if found.skill in SKILLS else {"dc": found.dc},
                        keywords=[]))
            facts += 1
    for page, rows in extraction.tables:
        text = "\n".join(" | ".join(row) for row in rows)
        chunk = DocumentChunk(document_id=document.id, campaign_id=document.campaign_id, ordinal=len(chunks),
                              page_start=page, page_end=page, section="Tabla", kind="table", text=text[:8000],
                              knowledge_level="dm", classification_reason="Tabla (revisar si es pública).")
        db.add(chunk)
        chunks.append(chunk)
    _progress(db, document, 70, f"{len(chunks)} fragmentos, {len(scenes)} escenas y {facts} hechos con CD detectados.")

    maps = 0
    for image in extraction.images:
        text = image.nearby_text.lower()
        is_map = image.page_coverage > 0.35 and any(w in text for w in MAP_WORDS)
        is_map = is_map or (image.page_coverage > 0.6 and min(image.width, image.height) > 600)
        maps += int(is_map)
        db.add(DocumentAsset(document_id=document.id, campaign_id=document.campaign_id, page=image.page,
                             file_path=str(image.path), width=image.width, height=image.height,
                             kind="map" if is_map else "illustration", knowledge_level="dm"))
    _progress(db, document, 80, f"{len(extraction.images)} imágenes guardadas ({maps} posibles mapas).")

    embedded = embed_chunks(db, chunks, provider)
    document.status = "ready"
    _progress(db, document, 100, f"Listo. {embedded} fragmentos con búsqueda semántica."
              if embedded else "Listo. Búsqueda por palabras (Ollama no disponible para búsqueda semántica).")
    append_event(db, document.campaign_id, "document_ready", {"document_id": document.id, "title": document.title},
                 visibility="dm")
    db.commit()


def embed_chunks(db: Session, chunks: list[DocumentChunk], provider: LLMProvider | None, batch: int = 16) -> int:
    if provider is None:
        return 0
    done = 0
    for start in range(0, len(chunks), batch):
        group = chunks[start : start + batch]
        try:
            vectors = provider.embed([f"{c.section}\n{c.text}"[:6000] for c in group])
        except LLMUnavailable as exc:
            log.info("Sin embeddings: %s", exc)
            return done
        for chunk, vector in zip(group, vectors, strict=False):
            array = np.asarray(vector, dtype=np.float32)
            norm = float(np.linalg.norm(array)) or 1.0
            chunk.embedding = (array / norm).tobytes()
            done += 1
        db.flush()
    return done


def document_summary(document: Document) -> dict[str, Any]:
    return {
        "id": document.id,
        "title": document.title,
        "filename": document.filename,
        "page_count": document.page_count,
        "status": document.status,
        "progress": document.progress,
        "log": document.log,
        "created_at": document.created_at.isoformat(),
    }
