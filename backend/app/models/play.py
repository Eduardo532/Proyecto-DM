"""Sesiones, eventos inmutables, tiradas, memoria y combate."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_id, utc_now


class GameSession(Base):
    __tablename__ = "session"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(20), default="exploring", nullable=False)
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scene.id", ondelete="SET NULL"))
    active_player_id: Mapped[str | None] = mapped_column(ForeignKey("player.id", ondelete="SET NULL"))
    ai_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("campaign_id", "number"),
        CheckConstraint(
            "state in ('exploring', 'awaiting_roll', 'combat', 'paused', 'closed')", name="state"
        ),
    )


class Event(Base):
    """Registro inmutable de todo lo que ocurre. Las correcciones son eventos nuevos."""

    __tablename__ = "event"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("session.id", ondelete="SET NULL"), index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(10), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # "public", "dm" o "character:<id>"
    visibility: Mapped[str] = mapped_column(String(50), default="public", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("campaign_id", "seq"),
        CheckConstraint("actor_kind in ('player', 'ai', 'dm', 'system')", name="actor_kind"),
    )


class DiceRoll(Base):
    __tablename__ = "dice_roll"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("session.id", ondelete="SET NULL"), index=True)
    character_id: Mapped[str | None] = mapped_column(ForeignKey("character.id", ondelete="SET NULL"))
    entity_id: Mapped[str | None] = mapped_column(ForeignKey("entity.id", ondelete="SET NULL"))
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    expression: Mapped[str] = mapped_column(String(100), nullable=False)
    ability: Mapped[str | None] = mapped_column(String(3))
    skill: Mapped[str | None] = mapped_column(String(30))
    advantage: Mapped[str] = mapped_column(String(15), default="none", nullable=False)
    mode: Mapped[str | None] = mapped_column(String(10))
    dice: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    natural: Mapped[int | None] = mapped_column(Integer)
    modifiers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    total: Mapped[int | None] = mapped_column(Integer)
    dc: Mapped[int | None] = mapped_column(Integer)
    dc_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="pending", nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(10))
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(10), default="ai", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("status in ('pending', 'resolved', 'void')", name="status"),
        CheckConstraint("mode is null or mode in ('digital', 'manual')", name="mode"),
    )


class MemoryEntry(Base):
    __tablename__ = "memory_entry"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(12), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    visibility: Mapped[str] = mapped_column(String(10), default="public", nullable=False)
    source_event_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    edited_by_dm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    superseded_by: Mapped[str | None] = mapped_column(ForeignKey("memory_entry.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("scope in ('campaign', 'character', 'npc', 'quest', 'location', 'session')", name="scope"),
        CheckConstraint("importance between 1 and 5", name="importance"),
        CheckConstraint("visibility in ('public', 'dm')", name="visibility"),
    )


class Combat(Base):
    """Estado de un encuentro activo: orden de iniciativa y recursos de cada turno."""

    __tablename__ = "combat"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("session.id", ondelete="SET NULL"))
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scene.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(10), default="active", nullable=False)
    round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # [{"entity_id", "name", "initiative", "dex_modifier", "speed_ft"}]
    order: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    budgets: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    removed: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    log: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
