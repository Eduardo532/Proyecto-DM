"""Documentos PDF: subida, procesamiento, revisión de la clasificación, imágenes y búsqueda."""

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
from app.models import Document, DocumentAsset, DocumentChunk
from app.services.errors import Forbidden, NotFound

router = APIRouter(tags=["documentos"])
MAX_UPLOAD_BYTES = 300 * 1024 * 1024


class ChunkUpdate(BaseModel):
    knowledge_level: Literal["public", "conditional", "dm"] | None = None
    scene_id: str | None = None


class AssetUpdate(BaseModel):
    kind: Literal["map", "illustration", "handout", "unknown"] | None = None
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
            process_document(db, document, runtime.settings.data_dir, runtime.provider)
        except Exception:
            return  # el error queda en document.log


@router.post("/campaigns/{campaign_id}/documents", response_model=dict[str, Any], status_code=202)
async def upload(campaign: DmCampaign, file: UploadFile, db: Db, request: Request) -> dict[str, Any]:
    if not (file.filename or "").lower().endswith(".pdf"):
        from app.engines.errors import RuleViolation

        raise RuleViolation("Solo se admiten archivos PDF.")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        size = 0
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                from app.engines.errors import RuleViolation

                raise RuleViolation("El PDF supera el tamaño máximo (300 MB).")
            tmp.write(chunk)
        temp_path = Path(tmp.name)
    try:
        settings = request.app.state.settings
        document = register_upload(db, campaign, settings.data_dir, file.filename or "documento.pdf", temp_path)
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
    return [{"id": a.id, "document_id": a.document_id, "page": a.page, "width": a.width, "height": a.height,
             "kind": a.kind, "knowledge_level": a.knowledge_level, "caption": a.caption}
            for a in db.scalars(query.order_by(DocumentAsset.page))]


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
