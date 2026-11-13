"""Importación de archivos (PDF, imágenes y ZIP), revisión de lo detectado, imágenes y búsqueda."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.runtime import runtime
from app.api.deps import CampaignDep, Db, DmCampaign, IsDm, commit
from app.document_processing.pipeline import document_summary, process_document, register_upload
from app.document_processing.search import search
from app.importing.detect import IMAGE_EXTENSIONS
from app.importing.service import process_import
from app.models import Document, DocumentAsset, DocumentChunk
from app.services.errors import Forbidden, NotFound

router = APIRouter(tags=["documentos"])
MAX_UPLOAD_BYTES = 1024 * 1024 * 1024
SUPPORTED_SUFFIXES = {".pdf", ".zip"} | IMAGE_EXTENSIONS


class ChunkUpdate(BaseModel):
    knowledge_level: Literal["public", "conditional", "dm"] | None = None
    scene_id: str | None = None


class AssetUpdate(BaseModel):
    kind: Literal["map", "illustration", "handout", "token", "marker", "unknown"] | None = None
    knowledge_level: Literal["public", "conditional", "dm"] | None = None
    caption: str | None = None


def _run_processing(document_id: str) -> None:
    if runtime.database is None or runtime.settings is None:
        return
    with runtime.database.session_factory() as db:
        document = db.get(Document, document_id)
        if document is None:
            return
        try:
            if document.parent_id:  # PDF que salió de un ZIP: ya se sabe que es una aventura
                process_document(db, document, runtime.settings.data_dir, runtime.provider)
            else:
                process_import(db, document, runtime.settings.data_dir, runtime.provider)
        except Exception:
            return  # el error queda en document.log


@router.post("/campaigns/{campaign_id}/documents", response_model=dict[str, Any], status_code=202)
async def upload(campaign: DmCampaign, file: UploadFile, db: Db, request: Request) -> dict[str, Any]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        from app.engines.errors import RuleViolation

        raise RuleViolation("Formato no admitido. Sube un PDF (aventura, ficha o mapa), una imagen o un ZIP.")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        size = 0
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                from app.engines.errors import RuleViolation

                raise RuleViolation("El archivo supera el tamaño máximo (1 GB).")
            tmp.write(chunk)
        temp_path = Path(tmp.name)
    try:
        settings = request.app.state.settings
        document = register_upload(db, campaign, settings.data_dir, file.filename or f"archivo{suffix}", temp_path)
        commit(db)
    finally:
        temp_path.unlink(missing_ok=True)
    if document.status in {"pending", "error"}:
        runtime.submit(_run_processing, document.id)
        db.refresh(document)
    return document_summary(document)


@router.get("/campaigns/{campaign_id}/documents", response_model=list[dict[str, Any]])
def list_documents(campaign: DmCampaign, db: Db) -> list[dict[str, Any]]:
    rows = db.scalars(select(Document).where(Document.campaign_id == campaign.id).order_by(Document.created_at))
    return [document_summary(d) for d in rows]


@router.post("/campaigns/{campaign_id}/documents/{document_id}/reprocess", response_model=dict[str, Any])
def reprocess(campaign: DmCampaign, document_id: str, db: Db) -> dict[str, Any]:
    document = db.get(Document, document_id)
    if document is None or document.campaign_id != campaign.id:
        raise NotFound("El documento no existe.")
    document.status = "pending"
    commit(db)
    runtime.submit(_run_processing, document.id)
    db.refresh(document)
    return document_summary(document)


@router.delete("/campaigns/{campaign_id}/documents/{document_id}", status_code=204)
def delete_document(campaign: DmCampaign, document_id: str, db: Db) -> None:
    document = db.get(Document, document_id)
    if document is None or document.campaign_id != campaign.id:
        raise NotFound("El documento no existe.")
    Path(document.file_path).unlink(missing_ok=True)
    db.delete(document)
    commit(db)


@router.get("/campaigns/{campaign_id}/chunks", response_model=list[dict[str, Any]])
def list_chunks(campaign: DmCampaign, db: Db, document_id: str | None = None, level: str | None = None,
                offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
    query = select(DocumentChunk).where(DocumentChunk.campaign_id == campaign.id)
    if document_id:
        query = query.where(DocumentChunk.document_id == document_id)
    if level:
        query = query.where(DocumentChunk.knowledge_level == level)
    query = query.order_by(DocumentChunk.document_id, DocumentChunk.ordinal).offset(offset).limit(min(limit, 500))
    rows = db.scalars(query)
    return [
        {"id": c.id, "document_id": c.document_id, "ordinal": c.ordinal, "page_start": c.page_start,
         "page_end": c.page_end, "section": c.section, "kind": c.kind, "text": c.text,
         "knowledge_level": c.knowledge_level, "classification_source": c.classification_source,
         "classification_reason": c.classification_reason, "scene_id": c.scene_id}
        for c in rows
    ]


@router.patch("/campaigns/{campaign_id}/chunks/{chunk_id}", response_model=dict[str, Any])
def update_chunk(campaign: DmCampaign, chunk_id: str, body: ChunkUpdate, db: Db) -> dict[str, Any]:
    chunk = db.get(DocumentChunk, chunk_id)
    if chunk is None or chunk.campaign_id != campaign.id:
        raise NotFound("El fragmento no existe.")
    if body.knowledge_level:
        chunk.knowledge_level = body.knowledge_level
        chunk.classification_source = "manual"
    if "scene_id" in body.model_fields_set:
        chunk.scene_id = body.scene_id
    commit(db)
    return {"id": chunk.id, "knowledge_level": chunk.knowledge_level, "scene_id": chunk.scene_id}


@router.get("/campaigns/{campaign_id}/assets", response_model=list[dict[str, Any]])
def list_assets(campaign: CampaignDep, db: Db, dm: IsDm, kind: str | None = None) -> list[dict[str, Any]]:
    query = select(DocumentAsset).where(DocumentAsset.campaign_id == campaign.id)
    if kind:
        query = query.where(DocumentAsset.kind == kind)
    if not dm:
        query = query.where(DocumentAsset.knowledge_level == "public")
    return [asset_out(a) for a in db.scalars(query.order_by(DocumentAsset.page, DocumentAsset.caption))]


def asset_out(asset: DocumentAsset) -> dict[str, Any]:
    return {"id": asset.id, "document_id": asset.document_id, "page": asset.page, "width": asset.width,
            "height": asset.height, "kind": asset.kind, "knowledge_level": asset.knowledge_level,
            "caption": asset.caption, "original_name": asset.original_name, "variant": asset.variant,
            "group_key": asset.group_key, "meta": asset.meta or {}}


@router.patch("/campaigns/{campaign_id}/assets/{asset_id}", response_model=dict[str, Any])
def update_asset(campaign: DmCampaign, asset_id: str, body: AssetUpdate, db: Db) -> dict[str, Any]:
    asset = db.get(DocumentAsset, asset_id)
    if asset is None or asset.campaign_id != campaign.id:
        raise NotFound("La imagen no existe.")
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(asset, key, value)
    commit(db)
    return {"id": asset.id, "kind": asset.kind, "knowledge_level": asset.knowledge_level}


@router.get("/campaigns/{campaign_id}/assets/{asset_id}/image")
def asset_image(campaign: CampaignDep, asset_id: str, db: Db, dm: IsDm, dm_token: str | None = None) -> FileResponse:
    from app.services.dm_auth import tokens

    asset = db.get(DocumentAsset, asset_id)
    if asset is None or asset.campaign_id != campaign.id or not Path(asset.file_path).is_file():
        raise NotFound("La imagen no existe.")
    allowed = dm or tokens.check(dm_token, campaign.id) or asset.knowledge_level == "public"
    if not allowed:
        raise Forbidden("Esta imagen solo está disponible en modo DM.")
    return FileResponse(asset.file_path)


@router.get("/campaigns/{campaign_id}/search", response_model=list[dict[str, Any]])
def search_campaign(campaign: CampaignDep, db: Db, dm: IsDm, q: str, limit: int = 8) -> list[dict[str, Any]]:
    levels = ("public", "conditional", "dm") if dm else ("public",)
    hits = search(db, campaign.id, q, levels=levels, limit=min(limit, 20), provider=runtime.provider)
    return [{"chunk_id": h.chunk_id, "text": h.text, "citation": h.citation, "knowledge_level": h.knowledge_level,
             "kind": h.kind} for h in hits]


@router.get("/ai/status", response_model=dict[str, Any])
def ai_status() -> dict[str, Any]:
    return runtime.provider.status()


# ------------------------------------------------------- revisión de importaciones ---
class ConfirmCharacter(BaseModel):
    player_id: str | None = None
    # Correcciones del DM sobre el borrador (mismos campos que al crear un personaje).
    overrides: dict[str, Any] = {}


def _manifest_item(db: Db, campaign_id: str, document_id: str, index: int) -> tuple[Document, dict[str, Any]]:
    document = db.get(Document, document_id)
    if document is None or document.campaign_id != campaign_id:
        raise NotFound("El documento no existe.")
    if not 0 <= index < len(document.manifest):
        raise NotFound("El elemento no existe.")
    return document, dict(document.manifest[index])


@router.post("/campaigns/{campaign_id}/documents/{document_id}/items/{index}/confirm", response_model=dict[str, Any])
def confirm_character(campaign: DmCampaign, document_id: str, index: int, body: ConfirmCharacter,
                      db: Db) -> dict[str, Any]:
    """Crea el personaje a partir del borrador leído de la ficha."""
    from app.api.characters import create_character
    from app.engines.errors import RuleViolation
    from app.schemas.character import CharacterCreate

    document, item = _manifest_item(db, campaign.id, document_id, index)
    if item.get("kind") != "character" or not item.get("draft"):
        raise RuleViolation("Este elemento no es una ficha de personaje.")
    if item.get("status") == "done":
        raise RuleViolation("Este personaje ya se creó.")
    data = {**item["draft"], **body.overrides, "player_id": body.player_id}
    character = create_character(campaign, CharacterCreate.model_validate(data), db)
    item.update(status="done", ref_type="character", ref_id=character.id)
    manifest = list(document.manifest)
    manifest[index] = item
    document.manifest = manifest
    commit(db)
    return document_summary(document)


@router.post("/campaigns/{campaign_id}/documents/{document_id}/items/{index}/dismiss", response_model=dict[str, Any])
def dismiss_item(campaign: DmCampaign, document_id: str, index: int, db: Db) -> dict[str, Any]:
    document, item = _manifest_item(db, campaign.id, document_id, index)
    item["status"] = "ignored"
    manifest = list(document.manifest)
    manifest[index] = item
    document.manifest = manifest
    commit(db)
    return document_summary(document)


@router.get("/campaigns/{campaign_id}/markers", response_model=list[dict[str, Any]])
def list_markers(campaign: CampaignDep, db: Db) -> list[dict[str, Any]]:
    """Iconos de estado importados (por ejemplo, un set de marcadores de Roll20) para dibujarlos en los tokens."""
    rows = db.scalars(select(DocumentAsset).where(DocumentAsset.campaign_id == campaign.id,
                                                  DocumentAsset.kind == "marker").order_by(DocumentAsset.caption))
    return [{"asset_id": a.id, "label": (a.meta or {}).get("label") or a.caption,
             "condition": (a.meta or {}).get("condition")} for a in rows]
