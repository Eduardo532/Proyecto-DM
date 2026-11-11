"""Recuperación híbrida (palabras + semántica) con el filtro de conocimiento DENTRO de la consulta (D-04)."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.ai.providers import LLMProvider, LLMUnavailable
from app.models import Document, DocumentChunk

WORD = re.compile(r"[\wáéíóúüñÁÉÍÓÚÜÑ]{3,}", re.UNICODE)
STOP = {"que", "los", "las", "del", "con", "por", "para", "una", "uno", "unos", "unas", "como", "the", "and",
        "with", "este", "esta", "esto", "hay", "sus", "mis", "quiero", "intento", "puedo"}


@dataclass
class Hit:
    chunk_id: str
    text: str
    section: str
    page_start: int
    page_end: int
    document_title: str
    knowledge_level: str
    kind: str
    score: float

    @property
    def citation(self) -> str:
        single = self.page_start == self.page_end
        pages = f"p. {self.page_start}" if single else f"pp. {self.page_start}-{self.page_end}"
        return f"{self.document_title}, {pages}" + (f", {self.section}" if self.section else "")


def fts_query(query: str) -> str | None:
    words = [w.lower() for w in WORD.findall(query) if w.lower() not in STOP]
    if not words:
        return None
    return " OR ".join(f'"{w}"' for w in dict.fromkeys(words))


def search(
    db: Session,
    campaign_id: str,
    query: str,
    *,
    levels: tuple[str, ...] = ("public",),
    limit: int = 5,
    scene_id: str | None = None,
    provider: LLMProvider | None = None,
) -> list[Hit]:
    """Busca fragmentos de la campaña. Solo devuelve fragmentos con nivel incluido en ``levels``."""
    ranks: dict[str, float] = {}
    match = fts_query(query)
    level_list = ",".join(f"'{lvl}'" for lvl in levels if lvl in {"public", "conditional", "dm"}) or "'public'"
    if match:
        rows = db.execute(
            text(
                "SELECT c.id FROM chunk_fts f JOIN document_chunk c ON c.id = f.chunk_id "
                f"WHERE chunk_fts MATCH :q AND c.campaign_id = :cid AND c.knowledge_level IN ({level_list}) "
                "ORDER BY bm25(chunk_fts) LIMIT 40"
            ),
            {"q": match, "cid": campaign_id},
        ).all()
        for position, row in enumerate(rows):
            ranks[row[0]] = ranks.get(row[0], 0.0) + 1.0 / (60 + position)
    if provider is not None:
        try:
            vector = np.asarray(provider.embed([query])[0], dtype=np.float32)
            vector /= float(np.linalg.norm(vector)) or 1.0
        except (LLMUnavailable, IndexError, ValueError):
            vector = None
        if vector is not None:
            candidates = db.execute(
                select(DocumentChunk.id, DocumentChunk.embedding).where(
                    DocumentChunk.campaign_id == campaign_id,
                    DocumentChunk.knowledge_level.in_(levels),
                    DocumentChunk.embedding.is_not(None),
                )
            ).all()
            if candidates:
                matrix = np.vstack([np.frombuffer(c[1], dtype=np.float32) for c in candidates])
                if matrix.shape[1] == vector.shape[0]:
                    scores = matrix @ vector
                    for position, index in enumerate(np.argsort(-scores)[:40]):
                        chunk_id = candidates[int(index)][0]
                        ranks[chunk_id] = ranks.get(chunk_id, 0.0) + 1.0 / (60 + position)
    if not ranks:
        return []
    chunks = {c.id: c for c in db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(list(ranks))))}
    titles = {d.id: d.title for d in db.scalars(select(Document).where(Document.campaign_id == campaign_id))}
    hits = []
    for chunk_id, score in ranks.items():
        chunk = chunks.get(chunk_id)
        if chunk is None or chunk.knowledge_level not in levels:
            continue
        if scene_id and chunk.scene_id == scene_id:
            score += 0.02  # refuerzo por cercanía a la escena actual
        hits.append(Hit(chunk.id, chunk.text, chunk.section, chunk.page_start, chunk.page_end,
                        titles.get(chunk.document_id, ""), chunk.knowledge_level, chunk.kind, score))
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]
