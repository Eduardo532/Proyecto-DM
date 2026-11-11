"""Resumen de sesión.

Sin modelo de lenguaje se construye un resumen determinista a partir de los eventos; con
modelo, la fase de IA lo enriquece y lo valida contra el estado.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import SUMMARY_SCHEMA
from app.ai.providers import LLMUnavailable, parse_json
from app.models import Character, Event, GameSession, MemoryEntry


def summarize_session(db: Session, session: GameSession) -> dict[str, Any]:
    """Resumen estructurado. Usa el modelo si está disponible y guarda un recuerdo de la sesión."""
    base = deterministic_summary(db, session)
    summary = dict(base)
    from app.ai.runtime import runtime

    narration = base.pop("_narracion", [])
    summary.pop("_narracion", None)
    try:
        raw = runtime.provider.chat(
            [
                {"role": "system", "content": "Eres el cronista de una campaña de rol. Resume con precisión, sin "
                                              "inventar nada que no esté en los datos."},
                {"role": "user", "content": "Datos de la sesión:\n" + "\n".join(
                    [*base["acontecimientos"], *base["descubrimientos"], *narration[-15:]])[:9000]},
            ],
            schema=SUMMARY_SCHEMA,
            aux=True,
        )
        enriched = parse_json(raw)
        for key in ("acontecimientos", "decisiones", "ganchos_abiertos"):
            if isinstance(enriched.get(key), list):
                summary[key] = [str(x) for x in enriched[key]][:20]
        if isinstance(enriched.get("situacion_final"), str) and enriched["situacion_final"].strip():
            summary["situacion_final"] = enriched["situacion_final"].strip()
        summary["generado_por"] = "ia"
    except (LLMUnavailable, ValueError):
        pass
    db.add(MemoryEntry(campaign_id=session.campaign_id, scope="session", scope_id=session.id, importance=4,
                       content=f"Sesión {session.number}: " + (summary.get("situacion_final") or "; ".join(
                           summary.get("acontecimientos", [])[-3:]))[:1500]))
    return summary


def deterministic_summary(db: Session, session: GameSession) -> dict[str, Any]:
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
        "decisiones": [],
        "ganchos_abiertos": [],
        "generado_por": "sistema",
        "_narracion": narration,
    }
