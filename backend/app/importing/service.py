"""Importación universal: un PDF, una imagen o un ZIP (con carpetas y ZIP anidados) se convierte en
aventuras procesadas, borradores de personaje, mapas con sus variantes, ilustraciones, tokens y marcadores.

Cada archivo deja un elemento en ``Document.manifest`` con lo detectado, el motivo y lo que se creó, para que
el DM pueda revisarlo. Las fichas de personaje quedan como borrador hasta que el DM las confirma.
"""

from __future__ import annotations

import importlib
import logging
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import LLMProvider
from app.document_processing.pipeline import campaign_dir, process_document, register_upload
from app.importing.detect import KIND_LABELS, Detected, detect_file
from app.importing.maps import (
    GRID_CONFIDENCE,
    GridGuess,
    cells_for,
    clean_stem,
    display_name,
    estimate_grid,
    fallback_cell,
)
from app.importing.zipwalk import ExtractedFile, extract_archive
from app.models import Campaign, Document, DocumentAsset, GameMap
from app.services.events import append_event

log = logging.getLogger("vdm.import")
PLAYER_ORDER = ("player", "nogrid", "default", "grid", "zones", "dm")
DM_ORDER = ("dm", "zones")


def process_import(db: Session, document: Document, data_dir: Path, provider: LLMProvider | None) -> None:
    try:
        _Importer(db, document, data_dir, provider).run()
    except Exception as exc:
        db.rollback()
        document.status = "error"
        document.log = [*document.log, f"Error: {exc}"]
        db.commit()
        log.exception("Error importando %s", document.filename)
        raise


class _Importer:
    def __init__(self, db: Session, document: Document, data_dir: Path, provider: LLMProvider | None) -> None:
        self.db = db
        self.document = document
        self.data_dir = data_dir
        self.provider = provider
        self.campaign = db.get(Campaign, document.campaign_id)
        self.work = campaign_dir(data_dir, document.campaign_id) / "imports" / document.id
        self.items: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ flujo ---
    def progress(self, value: int, message: str) -> None:
        self.document.progress = value
        self.document.log = [*self.document.log, message]
        self.document.manifest = [dict(item) for item in self.items]
        self.db.commit()

    def run(self) -> None:
        document = self.document
        source = Path(document.file_path)
        document.status = "processing"
        document.log = []
        self.progress(2, "Analizando el archivo…")
        files = self.collect(source)
        detections = []
        for index, extracted in enumerate(files):
            detections.append((extracted, detect_file(extracted.path, extracted.relative)))
            if index % 20 == 19:
                self.progress(5 + int(25 * index / len(files)), f"Reconocidos {index + 1} de {len(files)} archivos…")
        for _, found in detections:
            self.items.append(_item(found))
        counts: dict[str, int] = defaultdict(int)
        for _, found in detections:
            counts[found.kind] += 1
        summary = ", ".join(f"{KIND_LABELS.get(kind, kind).lower()}: {n}" for kind, n in sorted(counts.items()))
        self.progress(30, f"{len(files)} archivos: {summary}.")

        single = len(detections) == 1 and detections[0][0].path == source
        if single:
            document.kind = {"adventure": "pdf", "character": "sheet", "map": "map_pdf" if source.suffix.lower()
                             == ".pdf" else "image"}.get(detections[0][1].kind, document.kind)
        if single and detections[0][1].kind == "adventure":
            self.items[0].update(status="done", ref_type="document", ref_id=document.id)
            document.manifest = [dict(self.items[0])]
            self.db.commit()
            process_document(self.db, document, self.data_dir, self.provider)
            document.manifest = [dict(self.items[0])]
            self.db.commit()
            return
        self.clear_previous()
        self.import_adventures(detections, single)
        self.import_characters(detections)
        self.import_maps(detections)
        self.import_images(detections)
        for item in self.items:
            if item["status"] == "pending":
                item["status"] = "ignored"
        document.status = "ready"
        self.progress(100, "Importación terminada. Revisa lo detectado y confirma los personajes.")
        append_event(self.db, document.campaign_id, "document_ready",
                     {"document_id": document.id, "title": document.title}, visibility="dm")
        self.db.commit()

    def collect(self, source: Path) -> list[ExtractedFile]:
        if source.suffix.lower() != ".zip":
            return [ExtractedFile(source, self.document.filename)]
        target = self.work / "files"
        if target.exists():
            shutil.rmtree(target)
        return extract_archive(source, target)

    def clear_previous(self) -> None:
        """Reimportar: se quitan los mapas e imágenes que creó esta importación (no los personajes confirmados)."""
        assets = list(self.db.scalars(select(DocumentAsset).where(DocumentAsset.document_id == self.document.id)))
        ids = [a.id for a in assets]
        if ids:
            for game_map in self.db.scalars(select(GameMap).where(GameMap.background_asset_id.in_(ids),
                                                                   GameMap.origin == "import")):
                self.db.delete(game_map)
            for asset in assets:
                self.db.delete(asset)
            self.db.flush()

    # -------------------------------------------------------------- aventuras ---
    def import_adventures(self, detections: list[tuple[ExtractedFile, Detected]], single: bool) -> None:
        adventures = [(i, e) for i, (e, d) in enumerate(detections) if d.kind == "adventure"]
        for position, (index, extracted) in enumerate(adventures):
            item = self.items[index]
            self.progress(32 + int(30 * position / max(1, len(adventures))), f"Procesando la aventura {item['name']}…")
            assert self.campaign is not None
            child = register_upload(self.db, self.campaign, self.data_dir, Path(extracted.relative).name,
                                    extracted.path, title=item["name"], parent_id=self.document.id)
            self.db.commit()
            item.update(ref_type="document", ref_id=child.id)
            if child.status in {"pending", "error"}:
                try:
                    process_document(self.db, child, self.data_dir, self.provider)
                except Exception as exc:  # el error queda en el registro del documento hijo
                    item.update(status="error", warnings=[str(exc)])
                    continue
            item["status"] = "done"

    # ------------------------------------------------------------- personajes ---
    def import_characters(self, detections: list[tuple[ExtractedFile, Detected]]) -> None:
        from app.importing.sheets.reader import read_sheet

        for index, (extracted, found) in enumerate(detections):
            if found.kind != "character":
                continue
            item = self.items[index]
            sheet = read_sheet(extracted.path)
            if sheet is None:
                item.update(status="error", warnings=["No se pudo leer la ficha."])
                continue
            item.update(status="draft", draft=sheet.to_character(), warnings=list(sheet.warnings))
        self.progress(65, "Fichas de personaje leídas (pendientes de confirmar).")

    # ------------------------------------------------------------------ mapas ---
    def import_maps(self, detections: list[tuple[ExtractedFile, Detected]]) -> None:
        groups: dict[str, list[tuple[int, Path, Detected]]] = defaultdict(list)
        for index, (extracted, found) in enumerate(detections):
            if found.kind != "map":
                continue
            path = extracted.path
            if path.suffix.lower() == ".pdf":
                rendered = render_pdf_map(path, self.work / "maps" / f"{index:04d}.png")
                if rendered is None:
                    self.items[index].update(status="error", warnings=["No se pudo convertir el PDF en imagen."])
                    continue
                path = rendered
            folder = str(Path(extracted.relative).parent)
            groups[f"{folder}|{found.group_key or found.name}"].append((index, path, found))
        for members in groups.values():
            self.create_map(members)
        self.progress(85, f"{len(groups)} mapas creados.")

    def create_map(self, members: list[tuple[int, Path, Detected]]) -> None:
        from PIL import Image

        assets: dict[str, DocumentAsset] = {}
        for index, path, found in members:
            try:
                with Image.open(path) as image:
                    width, height = image.size
            except (OSError, ValueError):
                self.items[index].update(status="error", warnings=["La imagen no se puede abrir."])
                continue
            variant = found.variant or "default"
            if variant in assets:
                variant = f"{variant}{len(assets)}"
            asset = DocumentAsset(document_id=self.document.id, campaign_id=self.document.campaign_id, page=0,
                                  file_path=str(path), width=width, height=height, kind="map", knowledge_level="dm",
                                  caption=found.name[:400], original_name=found.relative[-300:],
                                  group_key=found.group_key[:200], variant=variant[:20])
            self.db.add(asset)
            self.db.flush()
            assets[variant] = asset
            self.items[index].update(status="done", ref_type="asset", ref_id=asset.id)
        if not assets:
            return
        player = next((assets[v] for v in PLAYER_ORDER if v in assets), next(iter(assets.values())))
        dm = next((assets[v] for v in DM_ORDER if v in assets and assets[v] is not player), None)
        grid_source = assets.get("grid") or player
        guess = estimate_grid(Path(grid_source.file_path))
        same_size = (grid_source.width, grid_source.height) == (player.width, player.height)
        if guess is None or guess.confidence < GRID_CONFIDENCE or not same_size:
            if "grid" in assets and guess is not None and guess.confidence >= GRID_CONFIDENCE:
                player = assets["grid"]
            else:
                cell = fallback_cell(player.width, player.height)
                guess = GridGuess(cell, cell, 0.0, 0.0, 0.0)
        elif player.variant == "grid" and "nogrid" in assets:
            # Con la cuadrícula ya medida, a la mesa se le muestra la versión limpia (la app dibuja la suya).
            player = assets["nogrid"]
        columns, rows = cells_for(int(player.width - guess.offset_x), int(player.height - guess.offset_y),
                                  guess.cell_w, guess.cell_h)
        name = display_name(members[0][2].name) or clean_stem(members[0][2].relative)
        game_map = GameMap(
            campaign_id=self.document.campaign_id, name=name[:200], origin="import", background_asset_id=player.id,
            dm_background_asset_id=dm.id if dm else None, width_cells=columns, height_cells=rows,
            cell_size_px=guess.cell_w, cell_height_px=None if guess.square else guess.cell_h,
            grid_offset_x=guess.offset_x, grid_offset_y=guess.offset_y,
            logic={"terrain": [], "doors": [], "lights": []}, explored=[],
        )
        self.db.add(game_map)
        self.db.flush()
        detail = (f"cuadrícula detectada {guess.cell_w:g} x {guess.cell_h:g} px" if guess.confidence
                  else "sin cuadrícula detectable: ajústala en el editor de mapas")
        for index, _, _ in members:
            item = self.items[index]
            if item["status"] == "done":
                item.update(map_id=game_map.id, warnings=[f"Mapa «{name}»: {detail}."])
        append_event(self.db, self.document.campaign_id, "map_imported", {"map_id": game_map.id, "name": name},
                     visibility="dm")

    # ----------------------------------------------------- imágenes sueltas ---
    def import_images(self, detections: list[tuple[ExtractedFile, Detected]]) -> None:
        existing_markers = {
            (a.meta or {}).get("condition") or str((a.meta or {}).get("label", "")).lower()
            for a in self.db.scalars(select(DocumentAsset).where(DocumentAsset.campaign_id == self.document.campaign_id,
                                                                 DocumentAsset.kind == "marker"))
        }
        for index, (extracted, found) in enumerate(detections):
            if found.kind not in {"handout", "token", "marker"}:
                continue
            item = self.items[index]
            meta: dict[str, Any] = dict(found.meta)
            if found.kind == "marker":
                key = meta.get("condition") or str(meta.get("label", "")).lower()
                if key in existing_markers:
                    item.update(status="ignored", reason="Marcador repetido (otra versión del mismo icono).")
                    continue
                existing_markers.add(key)
            asset = DocumentAsset(
                document_id=self.document.id, campaign_id=self.document.campaign_id, page=0,
                file_path=str(extracted.path), width=found.width, height=found.height, kind=found.kind,
                # Tokens y marcadores son iconos de mesa; las ilustraciones las revela el DM cuando quiera.
                knowledge_level="dm" if found.kind == "handout" else "public",
                caption=found.name[:400], original_name=found.relative[-300:], meta=meta,
            )
            self.db.add(asset)
            self.db.flush()
            item.update(status="done", ref_type="asset", ref_id=asset.id)


def _item(found: Detected) -> dict[str, Any]:
    return {
        "path": found.relative,
        "kind": found.kind,
        "name": found.name,
        "reason": found.reason,
        "status": "ignored" if found.kind in {"ignored", "archive"} else "pending",
        "variant": found.variant,
        "group_key": found.group_key,
        "meta": found.meta,
        "warnings": [],
    }


def render_pdf_map(path: Path, target: Path) -> Path | None:
    """Imagen de un PDF de mapa: la imagen incrustada más grande o, si no hay, la página renderizada."""
    try:
        pymupdf: Any = importlib.import_module("pymupdf")
    except ImportError:  # pragma: no cover
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    doc: Any = pymupdf.open(path)
    try:
        page = doc[0]
        images = page.get_images(full=True)
        if images:
            best = max(images, key=lambda info: int(info[2]) * int(info[3]))
            data = doc.extract_image(int(best[0]))
            if data and int(data.get("width", 0)) >= 500:
                image_target = target.with_suffix(f".{data.get('ext', 'png')}")
                image_target.write_bytes(data["image"])
                return image_target
        page.get_pixmap(dpi=150).save(str(target))
        return target
    except Exception:
        return None
    finally:
        doc.close()
