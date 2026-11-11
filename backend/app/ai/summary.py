"""Resumen de sesión.

Sin modelo de lenguaje se construye un resumen determinista a partir de los eventos; con
modelo, la fase de IA lo enriquece y lo valida contra el estado.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Character, Event, GameSession


def summarize_session(db: Session, session: GameSession) -> dict[str, Any]:
    events = list(
        db.scalars(
            select(Event)
            .where(Event.session_id == session.id, Event.visibility == "public")
            .order_by(Event.seq)
        )
    )
    actions = [e.payload for e in events if e.type == "player_action"]
    revealed = [e.payload.get("statement", "") for e in events if e.type == "fact_revealed"]
    narration = [e.payload.get("text", "") for e in events if e.type == "narration"]
    rolls = [e.payload for e in events if e.type == "roll_resolved"]
    characters = sorted({str(a.get("name")) for a in actions if a.get("name")})
    states = []
    for character in db.scalars(select(Character).where(Character.campaign_id == session.campaign_id)):
        states.append(f"{character.name}: {character.hp_current}/{character.hp_max} PG"
                      + (f", {', '.join(character.conditions)}" if character.conditions else ""))
    return {
        "acontecimientos": [f"{a.get('name')}: {a.get('text')}" for a in actions][-30:],
        "descubrimientos": revealed,
        "personajes_presentes": characters,
        "tiradas": [f"{r.get('label')}: {r.get('total')} ({r.get('outcome') or 'sin CD'})" for r in rolls][-30:],
        "cambios_de_estado": states,
        "situacion_final": narration[-1] if narration else "",
        "generado_por": "sistema",
    }
