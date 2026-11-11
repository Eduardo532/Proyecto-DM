"""Documentos PDF, fragmentos, escenas, mapas, entidades y hechos (conocimiento)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_id, utc_now
from app.models.campaign import TimestampMixin

KNOWLEDGE_CHECK = "knowledge_level in ('public', 'conditional', 'dm')"


class Document(TimestampMixin, Base):
    __tablename__ = "document"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    log: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    __table_args__ = (
        UniqueConstraint("campaign_id", "sha256"),
        CheckConstraint("status in ('pending', 'processing', 'ready', 'error')", name="status"),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunk"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="narrative", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Cerrado por defecto: hasta que se clasifica, todo es exclusivo del DM.
    knowledge_level: Mapped[str] = mapped_column(String(12), default="dm", nullable=False)
    classification_source: Mapped[str] = mapped_column(String(10), default="auto", nullable=False)
    classification_reason: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scene.id", ondelete="SET NULL"))
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary)

    __table_args__ = (CheckConstraint(KNOWLEDGE_CHECK, name="knowledge_level"),)


class DocumentAsset(Base):
    __tablename__ = "document_asset"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    knowledge_level: Mapped[str] = mapped_column(String(12), default="dm", nullable=False)
    caption: Mapped[str] = mapped_column(String(400), default="", nullable=False)

    __table_args__ = (CheckConstraint(KNOWLEDGE_CHECK, name="knowledge_level"),)


class Scene(TimestampMixin, Base):
    __tablename__ = "scene"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    summary_public: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary_dm: Mapped[str] = mapped_column(Text, default="", nullable=False)
    map_id: Mapped[str | None] = mapped_column(ForeignKey("map.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="unvisited", nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lighting: Mapped[str] = mapped_column(String(10), default="bright", nullable=False)


class GameMap(TimestampMixin, Base):
    __tablename__ = "map"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    origin: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    background_asset_id: Mapped[str | None] = mapped_column(ForeignKey("document_asset.id", ondelete="SET NULL"))
    width_cells: Mapped[int] = mapped_column(Integer, nullable=False)
    height_cells: Mapped[int] = mapped_column(Integer, nullable=False)
    cell_size_ft: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    grid_offset_x: Mapped[float] = mapped_column(default=0.0, nullable=False)
    grid_offset_y: Mapped[float] = mapped_column(default=0.0, nullable=False)
    cell_size_px: Mapped[float] = mapped_column(default=50.0, nullable=False)
    ambient_light: Mapped[str] = mapped_column(String(10), default="bright", nullable=False)
    # Capa lógica: {"terrain": [[x, y, "wall"], ...], "doors": [[x, y, "closed"], ...], "lights": [...]}
    logic: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    fog_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    explored: Mapped[list[list[int]]] = mapped_column(JSON, default=list, nullable=False)

    __table_args__ = (
        CheckConstraint("width_cells between 1 and 200 and height_cells between 1 and 200", name="size"),
    )


class Entity(TimestampMixin, Base):
    """Presencia de una criatura u objeto en una escena (estado real del mundo)."""

    __tablename__ = "entity"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scene.id", ondelete="CASCADE"), index=True)
    map_id: Mapped[str | None] = mapped_column(ForeignKey("map.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    character_id: Mapped[str | None] = mapped_column(ForeignKey("character.id", ondelete="CASCADE"))
    npc_id: Mapped[str | None] = mapped_column(ForeignKey("npc.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_public: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    x: Mapped[int | None] = mapped_column(Integer)
    y: Mapped[int | None] = mapped_column(Integer)
    size: Mapped[str] = mapped_column(String(12), default="medium", nullable=False)
    hp_current: Mapped[int | None] = mapped_column(Integer)
    hp_max: Mapped[int | None] = mapped_column(Integer)
    armor_class: Mapped[int | None] = mapped_column(Integer)
    conditions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    disposition: Mapped[str] = mapped_column(String(10), default="neutral", nullable=False)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    token_color: Mapped[str] = mapped_column(String(20), default="#8b1e1e", nullable=False)

    __table_args__ = (
        CheckConstraint("kind in ('character', 'npc', 'creature', 'object')", name="kind"),
        CheckConstraint("disposition in ('ally', 'neutral', 'hostile')", name="disposition"),
    )


class Fact(TimestampMixin, Base):
    """Un hecho del mundo y su nivel de conocimiento."""

    __tablename__ = "fact"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scene.id", ondelete="SET NULL"), index=True)
    subject: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_level: Mapped[str] = mapped_column(String(12), default="dm", nullable=False)
    # {"skill": "investigation", "dc": 15} o {"tiers": [[10, "texto"], ...]}
    discovery: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source_chunk_id: Mapped[str | None] = mapped_column(ForeignKey("document_chunk.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="true", nullable=False)

    __table_args__ = (
        CheckConstraint(KNOWLEDGE_CHECK, name="knowledge_level"),
        CheckConstraint("status in ('true', 'false_rumor', 'hypothesis')", name="status"),
    )


class FactAwareness(Base):
    __tablename__ = "fact_awareness"

    fact_id: Mapped[str] = mapped_column(ForeignKey("fact.id", ondelete="CASCADE"), primary_key=True)
    knower_kind: Mapped[str] = mapped_column(String(12), primary_key=True)
    knower_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    learned_event_id: Mapped[str | None] = mapped_column(ForeignKey("event.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (CheckConstraint("knower_kind in ('party', 'character', 'npc')", name="knower_kind"),)
