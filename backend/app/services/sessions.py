"""Sesiones de juego."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Campaign, GameSession
from app.models.base import utc_now
from app.services.errors import Conflict
from app.services.events import append_event


def open_session(db: Session, campaign_id: str) -> GameSession | None:
    return db.scalar(
        select(GameSession)
        .where(GameSession.campaign_id == campaign_id, GameSession.state != "closed")
        .order_by(GameSession.number.desc())
    )


def last_closed(db: Session, campaign_id: str) -> GameSession | None:
    return db.scalar(
        select(GameSession)
        .where(GameSession.campaign_id == campaign_id, GameSession.state == "closed")
        .order_by(GameSession.number.desc())
    )


def start_session(db: Session, campaign: Campaign) -> GameSession:
    current = open_session(db, campaign.id)
    if current:
        return current
    number = (db.scalar(select(func.max(GameSession.number)).where(GameSession.campaign_id == campaign.id)) or 0) + 1
    previous = last_closed(db, campaign.id)
    session = GameSession(
        campaign_id=campaign.id,
        number=number,
        scene_id=previous.scene_id if previous else None,
        active_player_id=previous.active_player_id if previous else None,
    )
    db.add(session)
    db.flush()
    append_event(db, campaign.id, "session_started", {"number": number}, session_id=session.id)
    return session


def close_session(db: Session, session: GameSession, summary: dict[str, Any]) -> GameSession:
    if session.state == "closed":
        raise Conflict("La sesión ya está cerrada.")
    session.state = "closed"
    session.ended_at = utc_now()
    session.summary = summary
    append_event(db, session.campaign_id, "session_closed", {"number": session.number, "summary": summary},
                 session_id=session.id)
    return session


def set_state(db: Session, session: GameSession, state: str) -> None:
    if session.state == "closed":
        raise Conflict("La sesión está cerrada.")
    session.state = state
