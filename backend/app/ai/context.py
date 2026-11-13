"""Construcción del contexto que recibe el modelo, con presupuesto de tamaño.

Hay dos tipos de contexto y nunca se mezclan:
- ``rules_context``: para clasificar la acción. Incluye los hechos ocultos de la escena porque su salida
  es un formulario que la mesa no ve.
- ``narration_context``: para escribir lo que la mesa lee. Solo contiene información pública o ya descubierta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.document_processing.classify import player_text
from app.document_processing.search import search
from app.models import Character, Entity, Event, Fact, FactAwareness, GameSession, MemoryEntry, Npc, Scene
from app.services import world
from app.services.characters import derived


@dataclass
class TurnContext:
    session: GameSession
    scene: Scene | None
    character: Character | None
    hidden_facts: list[Fact] = field(default_factory=list)
    npcs: list[Npc] = field(default_factory=list)
    budget_chars: int = 16000


def unrevealed_facts(db: Session, campaign_id: str, scene_id: str | None) -> list[Fact]:
    known = select(FactAwareness.fact_id)
    query = select(Fact).where(Fact.campaign_id == campaign_id, Fact.knowledge_level != "public",
                               Fact.id.not_in(known))
    if scene_id:
        query = query.where((Fact.scene_id == scene_id) | (Fact.scene_id.is_(None)))
    return list(db.scalars(query.order_by(Fact.created_at).limit(12)))


def _trim(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def recent_story(db: Session, campaign_id: str, limit: int = 8) -> list[str]:
    rows = db.scalars(
        select(Event)
        .where(Event.campaign_id == campaign_id, Event.visibility == "public",
               Event.type.in_(("player_action", "narration", "roll_resolved", "fact_revealed")))
        .order_by(Event.seq.desc())
        .limit(limit)
    )
    lines = []
    for event in reversed(list(rows)):
        p = event.payload
        if event.type == "player_action":
            lines.append(f"{p.get('name')}: {p.get('text')}")
        elif event.type == "narration":
            lines.append(f"DM: {_trim(str(p.get('text', '')), 240)}")
        elif event.type == "roll_resolved":
            lines.append(f"(Tirada: {p.get('label')} = {p.get('total')}, {p.get('outcome') or 'sin CD'})")
        else:
            lines.append(f"(Descubierto: {player_text(str(p.get('statement', '')))})")
    return lines


def scene_public_text(db: Session, scene: Scene | None) -> str:
    if scene is None:
        return "Escena sin definir."
    parts = [f"Escena: {scene.name}."]
    if scene.summary_public:
        parts.append(f"<documento>{_trim(scene.summary_public, 1500)}</documento>")
    light = {"bright": "bien iluminada", "dim": "en penumbra", "dark": "a oscuras"}.get(scene.lighting, "")
    if light:
        parts.append(f"La zona está {light}.")
    return "\n".join(parts)


def visible_entities_text(db: Session, campaign_id: str, scene_id: str | None) -> str:
    seen = [e for e in world.entities_for_players(db, campaign_id, scene_id) if e["kind"] != "character"]
    if not seen:
        return "No hay criaturas visibles además del grupo."
    lines = []
    for entity in seen:
        health = f", {entity['health']}" if entity.get("health") else ""
        lines.append(f"- {entity['name']} ({entity['disposition']}{health})")
    return "Visibles:\n" + "\n".join(lines)


def party_text(db: Session, campaign_id: str) -> str:
    lines = []
    for character in db.scalars(select(Character).where(Character.campaign_id == campaign_id,
                                                         Character.status != "retired")):
        state = f"{character.hp_current}/{character.hp_max} PG"
        if character.conditions:
            state += ", " + ", ".join(character.conditions)
        lines.append(f"- {character.name} ({character.race} {character.char_class} {character.level}): {state}")
    return "Grupo:\n" + ("\n".join(lines) or "- (sin personajes)")


def known_facts_text(db: Session, campaign_id: str, limit: int = 10) -> str:
    facts = world.known_facts(db, campaign_id)[-limit:]
    if not facts:
        return ""
    return "Lo que el grupo sabe:\n" + "\n".join(f"- {player_text(f.statement)}" for f in facts)


def memory_text(db: Session, campaign_id: str, limit: int = 6) -> str:
    rows = list(db.scalars(
        select(MemoryEntry)
        .where(MemoryEntry.campaign_id == campaign_id, MemoryEntry.visibility == "public",
               MemoryEntry.superseded_by.is_(None))
        .order_by(MemoryEntry.importance.desc(), MemoryEntry.created_at.desc())
        .limit(limit)
    ))
    if not rows:
        return ""
    return "Recuerdos de la campaña:\n" + "\n".join(f"- {m.content}" for m in rows)


def character_text(character: Character) -> str:
    d = derived(character)
    skills = ", ".join(f"{k} {v:+d}" for k, v in sorted(d.skills.items(), key=lambda kv: -kv[1])[:6])
    return (f"Personaje que actúa: {character.name}, {character.race} {character.char_class} de nivel "
            f"{character.level}. PG {character.hp_current}/{character.hp_max}, CA {character.armor_class}. "
            f"Mejores habilidades: {skills}.")


def rules_context(db: Session, ctx: TurnContext, action_text: str) -> tuple[str, dict[str, str], dict[str, str]]:
    """Contexto para clasificar. Devuelve el texto y los códigos H1.. / P1.. de hechos y PNJ."""
    fact_codes = {f"H{i + 1}": f.id for i, f in enumerate(ctx.hidden_facts)}
    npc_codes = {f"P{i + 1}": n.id for i, n in enumerate(ctx.npcs)}
    parts = [scene_public_text(db, ctx.scene)]
    if ctx.scene and ctx.scene.summary_dm:
        parts.append(f"Notas del DM sobre la escena:\n<documento>{_trim(ctx.scene.summary_dm, 1500)}</documento>")
    parts.append(visible_entities_text(db, ctx.session.campaign_id, ctx.scene.id if ctx.scene else None))
    if ctx.character:
        parts.append(character_text(ctx.character))
    if ctx.hidden_facts:
        parts.append("Hechos ocultos de la escena (código: descripción):\n" + "\n".join(
            f"{code}: {_trim(f.statement, 300)}" for code, f in zip(fact_codes, ctx.hidden_facts, strict=False)))
    if ctx.npcs:
        parts.append("PNJ presentes (código: nombre):\n" + "\n".join(
            f"{code}: {n.name} — {_trim(n.public_description, 120)}"
            for code, n in zip(npc_codes, ctx.npcs, strict=False)))
    story = recent_story(db, ctx.session.campaign_id, 4)
    if story:
        parts.append("Últimos acontecimientos:\n" + "\n".join(story))
    parts.append(f"Acción declarada: {action_text}")
    return _trim("\n\n".join(parts), ctx.budget_chars), fact_codes, npc_codes


def narration_context(db: Session, ctx: TurnContext, query: str, provider: object | None = None) -> str:
    """Contexto para narrar: solo información pública o ya descubierta."""
    campaign_id = ctx.session.campaign_id
    scene_id = ctx.scene.id if ctx.scene else None
    parts = [scene_public_text(db, ctx.scene), visible_entities_text(db, campaign_id, scene_id),
             party_text(db, campaign_id)]
    hits = search(db, campaign_id, query, levels=("public",), limit=2, scene_id=ctx.scene.id if ctx.scene else None)
    for hit in hits:
        parts.append(f"<documento fuente=\"{hit.citation}\">{_trim(hit.text, 1200)}</documento>")
    for block in (known_facts_text(db, campaign_id), memory_text(db, campaign_id)):
        if block:
            parts.append(block)
    story = recent_story(db, campaign_id)
    if story:
        parts.append("Historia reciente:\n" + "\n".join(story))
    return _trim("\n\n".join(parts), ctx.budget_chars)


def npcs_in_scene(db: Session, campaign_id: str, scene_id: str | None) -> list[Npc]:
    if scene_id is None:
        return []
    ids = select(Entity.npc_id).where(Entity.scene_id == scene_id, Entity.npc_id.is_not(None),
                                      Entity.hidden.is_(False))
    return list(db.scalars(select(Npc).where(Npc.campaign_id == campaign_id, Npc.id.in_(ids))))
