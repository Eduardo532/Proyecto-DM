"""Campañas, participantes, personajes, PNJ y misiones."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_id, utc_now


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaign"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    game_system: Mapped[str] = mapped_column(String(40), default="dnd5e_2014", nullable=False)
    dice_mode: Mapped[str] = mapped_column(String(10), default="ask", nullable=False)
    dm_pin_hash: Mapped[str | None] = mapped_column(String(200))
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    __table_args__ = (
        CheckConstraint("dice_mode in ('digital', 'manual', 'ask')", name="dice_mode"),
        CheckConstraint("status in ('active', 'archived')", name="status"),
    )


class Player(TimestampMixin, Base):
    __tablename__ = "player"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#b8913a", nullable=False)
    turn_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint("campaign_id", "display_name"),)


class Character(TimestampMixin, Base):
    __tablename__ = "character"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id: Mapped[str | None] = mapped_column(ForeignKey("player.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    race: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    char_class: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    subclass: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    background: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    alignment: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Características, competencias, ataques, conjuros, rasgos, inventario, monedas... (validado con Pydantic)
    sheet: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    hp_max: Mapped[int] = mapped_column(Integer, nullable=False)
    hp_current: Mapped[int] = mapped_column(Integer, nullable=False)
    hp_temp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    armor_class: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    speed_ft: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    conditions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    exhaustion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    death_saves: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    stable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    portrait_url: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        CheckConstraint("level between 1 and 20", name="level"),
        CheckConstraint("hp_current >= 0 and hp_current <= hp_max", name="hp_range"),
        CheckConstraint("hp_temp >= 0", name="hp_temp"),
        CheckConstraint("status in ('active', 'dead', 'retired')", name="status"),
    )


class CharacterChange(Base):
    __tablename__ = "character_change"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    character_id: Mapped[str] = mapped_column(ForeignKey("character.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("event.id", ondelete="SET NULL"))
    field: Mapped[str] = mapped_column(String(60), nullable=False)
    before: Mapped[Any] = mapped_column(JSON)
    after: Mapped[Any] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Npc(TimestampMixin, Base):
    __tablename__ = "npc"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    public_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    personality: Mapped[str] = mapped_column(Text, default="", nullable=False)
    motivations: Mapped[str] = mapped_column(Text, default="", nullable=False)
    secrets: Mapped[str] = mapped_column(Text, default="", nullable=False)
    voice: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    attitude: Mapped[str] = mapped_column(String(20), default="indifferent", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="alive", nullable=False)
    known_to_party: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Quest(TimestampMixin, Base):
    __tablename__ = "quest"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description_public: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_dm: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)

    __table_args__ = (
        CheckConstraint("status in ('unknown', 'offered', 'active', 'completed', 'failed')", name="status"),
    )
