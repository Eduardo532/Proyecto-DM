"""Registro de eventos inmutable y difusión en tiempo real."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Event
from app.services.hub import hub


def append_event(
    db: Session,
    campaign_id: str,
    type: str,
    payload: dict[str, Any],
    *,
    actor_kind: str = "system",
    actor_id: str | None = None,
    session_id: str | None = None,
    visibility: str = "public",
    broadcast: bool = True,
) -> Event:
    """Añade un evento con número de secuencia consecutivo dentro de la campaña.

    La escritura forma parte de la transacción del llamador; la difusión se hace al confirmar.
    """
    seq = (db.scalar(select(func.max(Event.seq)).where(Event.campaign_id == campaign_id)) or 0) + 1
    event = Event(
        campaign_id=campaign_id,
        session_id=session_id,
        seq=seq,
        type=type,
        actor_kind=actor_kind,
        actor_id=actor_id,
        payload=payload,
        visibility=visibility,
    )
    db.add(event)
    db.flush()
    if broadcast:
        pending: list[Event] = db.info.setdefault("pending_broadcast", [])
        pending.append(event)
    return event


def event_to_dict(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "seq": event.seq,
        "type": event.type,
        "actor_kind": event.actor_kind,
        "actor_id": event.actor_id,
        "payload": event.payload,
        "visibility": event.visibility,
        "session_id": event.session_id,
        "created_at": event.created_at.isoformat(),
    }


def flush_broadcasts(db: Session) -> None:
    """Envía a los clientes los eventos de la transacción ya confirmada."""
    pending: list[Event] = db.info.pop("pending_broadcast", [])
    for event in pending:
        hub.publish(event.campaign_id, {"kind": "event", "event": event_to_dict(event)}, event.visibility)
