"""Puntos de entrada del motor narrativo (se completan en la fase de IA)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Campaign, DiceRoll


def schedule_turn(campaign_id: str, session_id: str, event_id: str) -> None:
    """Interpreta una acción de jugador en segundo plano."""


def after_roll(db: Session, campaign: Campaign, roll: DiceRoll) -> None:
    """Continúa la narración cuando se resuelve una tirada pedida por la IA."""


def schedule_enemy_turn(campaign_id: str) -> None:
    """Si el turno de combate es de un enemigo controlado por la IA, lo resuelve."""
