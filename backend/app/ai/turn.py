"""Motor narrativo en canal fijo (D-13).

El código dirige los pasos; el modelo clasifica rellenando un formulario cerrado y narra resultados que
el motor ya calculó. Todo cambio mecánico pasa por los servicios del motor.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import context as ctxmod
from app.ai.guard import leaks
from app.ai.providers import LLMUnavailable, parse_json
from app.ai.prompts import SYSTEM_CLASSIFIER, SYSTEM_NARRATOR, classification_schema
from app.ai.runtime import runtime
from app.document_processing.classify import player_text
from app.engines.errors import RuleViolation
from app.engines.rules.abilities import SKILLS, skill_label
from app.engines.rules.checks import CheckKind, revealed_tiers
from app.models import Campaign, Character, DiceRoll, Entity, Event, Fact, GameSession, MemoryEntry, Npc, Scene
from app.services import combat as combat_service
from app.services import rolls as roll_service
from app.services import world
from app.services.events import append_event, flush_broadcasts
from app.services.hub import hub

log = logging.getLogger("vdm.ai")


# ------------------------------------------------------------ utilidades ---
def _status(campaign_id: str, busy: bool, text: str = "") -> None:
    hub.publish(campaign_id, {"kind": "ai_status", "busy": busy, "text": text})


def _budget() -> int:
    tokens = runtime.settings.llm_context_budget if runtime.settings else 5000
    return int(tokens * 3.2)


def _narrate(db: Session, ctx: ctxmod.TurnContext, instruction: str, query: str) -> str:
    """Pide la narración y aplica el filtro de fugas (un reintento; si persiste, texto neutro)."""
    context = ctxmod.narration_context(db, ctx, query)
    messages = [
        {"role": "system", "content": SYSTEM_NARRATOR},
        {"role": "user", "content": f"{context}\n\n{instruction}"},
    ]
    text = runtime.provider.chat(messages)
    hidden = ctxmod.unrevealed_facts(db, ctx.session.campaign_id, ctx.scene.id if ctx.scene else None)
    found = leaks(text, hidden)
    if found:
        log.warning("Posible fuga de secretos (%s); se reescribe.", found)
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": "Reescribe la narración sin mencionar: " + ", ".join(found)})
        text = runtime.provider.chat(messages)
        if leaks(text, hidden):
            append_event(db, ctx.session.campaign_id, "leak_blocked", {"terms": found, "text": text},
                         session_id=ctx.session.id, visibility="dm")
            text = "El DM se toma un momento para pensar… Describid de nuevo qué hacéis."
    return text.strip()


def _publish_narration(db: Session, session: GameSession, text: str, kind: str, **extra: Any) -> Event:
    return append_event(db, session.campaign_id, "narration", {"text": text, "kind": kind, **extra},
                        actor_kind="ai", session_id=session.id)


def _load(db: Session, session_id: str, character_id: str | None) -> ctxmod.TurnContext | None:
    session = db.get(GameSession, session_id)
    if session is None or session.state == "closed" or session.ai_paused:
        return None
    scene = db.get(Scene, session.scene_id) if session.scene_id else None
    character = db.get(Character, character_id) if character_id else None
    return ctxmod.TurnContext(
        session=session,
        scene=scene,
        character=character,
        hidden_facts=ctxmod.unrevealed_facts(db, session.campaign_id, scene.id if scene else None),
        npcs=ctxmod.npcs_in_scene(db, session.campaign_id, scene.id if scene else None),
        budget_chars=_budget(),
    )


def _run_safely(campaign_id: str, fn: Any, *args: Any) -> None:
    if runtime.database is None:
        return
    _status(campaign_id, True, "El DM está pensando…")
    with runtime.database.session_factory() as db:
        try:
            fn(db, *args)
            db.commit()
            flush_broadcasts(db)
        except LLMUnavailable as exc:
            db.rollback()
            append_event(db, campaign_id, "ai_unavailable", {"message": str(exc)}, actor_kind="system")
            db.commit()
            flush_broadcasts(db)
        except Exception:
            db.rollback()
            log.exception("Error en el motor narrativo")
            append_event(db, campaign_id, "ai_unavailable",
                         {"message": "El DM virtual tuvo un problema interno. Revisa los registros."})
            db.commit()
            flush_broadcasts(db)
        finally:
            _status(campaign_id, False)


# --------------------------------------------------------- acción libre ---
def schedule_turn(campaign_id: str, session_id: str, event_id: str) -> None:
    runtime.submit(_run_safely, campaign_id, run_turn, session_id, event_id)


Decision = tuple[dict[str, Any], dict[str, str], dict[str, str]]


def classify(db: Session, ctx: ctxmod.TurnContext, action_text: str) -> Decision:
    text, fact_codes, npc_codes = ctxmod.rules_context(db, ctx, action_text)
    schema = classification_schema(list(fact_codes), list(npc_codes))
    messages = [{"role": "system", "content": SYSTEM_CLASSIFIER}, {"role": "user", "content": text}]
    for _attempt in range(2):
        raw = runtime.provider.chat(messages, schema=schema, aux=True)
        try:
            decision = parse_json(raw)
            if decision.get("tipo") in schema["properties"]["tipo"]["enum"]:
                return decision, fact_codes, npc_codes
        except ValueError:
            pass
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "Responde solo con el JSON válido del formulario."})
    return {"tipo": "aclaracion", "pregunta": "¿Puedes describir con más detalle qué intenta hacer tu personaje?"}, \
        fact_codes, npc_codes


def run_turn(db: Session, session_id: str, event_id: str) -> None:
    event = db.get(Event, event_id)
    if event is None:
        return
    payload = event.payload
    ctx = _load(db, session_id, payload.get("character_id"))
    if ctx is None or ctx.character is None:
        return
    if payload.get("mode") == "talk":
        _talk(db, ctx, str(payload.get("text", "")))
        return
    action = f"{ctx.character.name} intenta: {payload.get('text', '')}"
    if payload.get("target"):
        action += f" (elemento seleccionado: {payload['target']})"
    decision, fact_codes, npc_codes = classify(db, ctx, action)
    kind = decision.get("tipo")
    fact_id = fact_codes.get(str(decision.get("hecho")))
    npc_id = npc_codes.get(str(decision.get("pnj")))
    append_event(db, ctx.session.campaign_id, "ai_decision", {"action_event_id": event.id, "decision": decision},
                 actor_kind="ai", session_id=ctx.session.id, visibility="dm")

    if kind == "requiere_tirada":
        if _request_roll(db, ctx, decision, fact_id, event.id):
            return
        kind = "automatica"  # la prueba propuesta no era válida: se trata como acción sin tirada
    if kind == "aclaracion":
        question = str(decision.get("pregunta") or "¿Qué quieres hacer exactamente?")
        _publish_narration(db, ctx.session, question, "clarify", character_id=ctx.character.id)
        return
    if kind == "combate":
        _start_combat(db, ctx, action)
        return
    if kind == "dialogo":
        _dialogue(db, ctx, action, npc_id)
        return
    outcome = {
        "automatica": "La acción tiene éxito sin necesidad de tirada.",
        "imposible": "La acción no es posible en estas circunstancias; explica por qué de forma narrativa.",
        "requiere_preparacion": "La acción necesita preparación o recursos previos; explica qué falta.",
    }.get(str(kind), "Describe lo que ocurre.")
    text = _narrate(db, ctx, f"{action}\nResultado (ya decidido): {outcome}\nNarra lo que ocurre.", action)
    _publish_narration(db, ctx.session, text, "result", character_id=ctx.character.id)


def _request_roll(db: Session, ctx: ctxmod.TurnContext, decision: dict[str, Any], fact_id: str | None,
                  action_event_id: str) -> bool:
    assert ctx.character is not None
    prueba = decision.get("prueba")
    skill = decision.get("habilidad") if decision.get("habilidad") in SKILLS else None
    ability = decision.get("caracteristica") if decision.get("caracteristica") in {"str", "dex", "con", "int", "wis",
                                                                                   "cha"} else None
    fact = db.get(Fact, fact_id) if fact_id else None
    dc = None
    if fact and fact.discovery.get("dc"):
        dc = int(fact.discovery["dc"])
        skill = fact.discovery.get("skill") or skill
    kind = CheckKind.SAVE if prueba == "salvacion" else CheckKind.SKILL if skill else CheckKind.ABILITY
    if kind is CheckKind.SKILL and not skill:
        return False
    if kind is not CheckKind.SKILL and not ability:
        ability = "wis" if kind is CheckKind.SAVE else None
        if ability is None:
            return False
    try:
        roll = roll_service.request_check(
            db, ctx.session, ctx.character, kind=kind, skill=skill if kind is CheckKind.SKILL else None,
            ability=ability if kind is not CheckKind.SKILL else None, dc=dc,
            difficulty=None if dc else str(decision.get("dificultad") or "media"),
            advantage=str(decision.get("ventaja") or "none"),
            reason=str(decision.get("intencion") or ""), requested_by="ai",
            context={"action_event_id": action_event_id, "fact_id": fact_id},
        )
    except RuleViolation as exc:
        log.info("Prueba propuesta no válida: %s", exc)
        return False
    label = skill_label(skill) if skill else roll.label.split(" — ")[0]
    _publish_narration(db, ctx.session, f"{ctx.character.name}, haz una prueba de {label}.", "roll_prompt",
                       character_id=ctx.character.id, roll_id=roll.id)
    return True


def _dialogue(db: Session, ctx: ctxmod.TurnContext, action: str, npc_id: str | None) -> None:
    assert ctx.character is not None
    npc = db.get(Npc, npc_id) if npc_id else None
    if npc is None:
        text = _narrate(db, ctx, f"{action}\nNarra la respuesta del entorno o de quien esté presente.", action)
        _publish_narration(db, ctx.session, text, "dialogue", character_id=ctx.character.id)
        return
    memories = db.scalars(select(MemoryEntry).where(MemoryEntry.scope == "npc", MemoryEntry.scope_id == npc.id,
                                                    MemoryEntry.superseded_by.is_(None)).limit(6))
    remembered = "\n".join(f"- {m.content}" for m in memories)
    persona = (f"Interpretas a {npc.name}. Descripción: {npc.public_description}. Personalidad: {npc.personality}. "
               f"Forma de hablar: {npc.voice}. Actitud hacia el grupo: {npc.attitude}.\n"
               f"Lo que {npc.name} recuerda:\n{remembered or '- nada relevante'}\n"
               f"{npc.name} solo sabe lo que se indica aquí; si le preguntan otra cosa, no lo sabe o lo evita.")
    text = _narrate(db, ctx, f"{persona}\n\n{action}\nResponde como {npc.name} (en estilo directo, 1-4 frases) "
                             "y añade como mucho una frase de narración.", action)
    _publish_narration(db, ctx.session, text, "dialogue", character_id=ctx.character.id, speaker=npc.name)
    db.add(MemoryEntry(campaign_id=npc.campaign_id, scope="npc", scope_id=npc.id, importance=2,
                       content=f"Habló con {ctx.character.name}: «{str(action)[:200]}»", visibility="dm"))
    npc.known_to_party = True


def _talk(db: Session, ctx: ctxmod.TurnContext, said: str) -> None:
    """Conversación libre: hablar con un PNJ, con el grupo o preguntar al DM. Nunca pide tiradas."""
    assert ctx.character is not None
    personas = []
    for npc in ctx.npcs:
        personas.append(f"- {npc.name}: {npc.public_description}. Personalidad: {npc.personality}. "
                        f"Habla así: {npc.voice}. Actitud: {npc.attitude}. Solo sabe lo que se indica aquí.")
    present = ("PNJ presentes:\n" + "\n".join(personas)) if personas else "No hay PNJ presentes."
    instruction = (
        f"{ctx.character.name} dice: «{said}»\n{present}\n"
        "Responde como Dungeon Master, en 1-4 frases:\n"
        "- Si se dirige a un PNJ presente, contesta ese PNJ en estilo directo, empezando por su nombre y dos puntos.\n"
        "- Si es una pregunta al DM (reglas, qué ve o qué sabe su personaje), contesta con lo que su personaje "
        "percibe o sabría, sin revelar secretos.\n"
        "- Si habla con otros personajes, no hables por ellos: como mucho añade un detalle del ambiente.\n"
        "No pidas tiradas ni decidas acciones de los personajes."
    )
    text = _narrate(db, ctx, instruction, said)
    _publish_narration(db, ctx.session, text, "dialogue", character_id=ctx.character.id)
    lowered = said.lower()
    for npc in ctx.npcs:
        if npc.name.lower().split(" ")[0] in lowered:
            db.add(MemoryEntry(campaign_id=npc.campaign_id, scope="npc", scope_id=npc.id, importance=2,
                               content=f"{ctx.character.name} le dijo: «{said[:200]}»", visibility="dm"))
            npc.known_to_party = True


def _start_combat(db: Session, ctx: ctxmod.TurnContext, action: str) -> None:
    session = ctx.session
    if combat_service.active_combat(db, session.campaign_id):
        text = _narrate(db, ctx, f"{action}\nEl combate ya está en curso. Describe brevemente la intención.", action)
        _publish_narration(db, session, text, "result")
        return
    scene_id = ctx.scene.id if ctx.scene else None
    visible = {e["id"] for e in world.entities_for_players(db, session.campaign_id, scene_id)}
    participants = [e.id for e in db.scalars(select(Entity).where(Entity.campaign_id == session.campaign_id,
                                                                    Entity.scene_id == scene_id))
                    if e.id in visible and (e.kind == "character" or e.disposition == "hostile")]
    if not any(db.get(Entity, pid).disposition == "hostile" for pid in participants):  # type: ignore[union-attr]
        text = _narrate(db, ctx, f"{action}\nNo hay enemigos a la vista. Narra la acción sin iniciar combate.", action)
        _publish_narration(db, session, text, "result")
        return
    combat = combat_service.start_combat(db, session, participants)
    order = ", ".join(c["name"] for c in combat.order)
    text = _narrate(db, ctx, f"{action}\nComienza el combate. Orden de iniciativa: {order}. "
                             "Describe el arranque en 2-3 frases.", action)
    _publish_narration(db, session, text, "combat")
    schedule_enemy_turn(session.campaign_id)


# -------------------------------------------------------- tras la tirada ---
def after_roll(db: Session, campaign: Campaign, roll: DiceRoll) -> None:
    if roll.requested_by == "ai" and roll.context.get("action_event_id"):
        runtime.submit(_run_safely, campaign.id, continue_after_roll, roll.id)


def continue_after_roll(db: Session, roll_id: str) -> None:
    roll = db.get(DiceRoll, roll_id)
    if roll is None or roll.session_id is None:
        return
    ctx = _load(db, roll.session_id, roll.character_id)
    if ctx is None or ctx.character is None:
        return
    action_event = db.get(Event, roll.context.get("action_event_id", ""))
    action = f"{ctx.character.name} intenta: {action_event.payload.get('text') if action_event else roll.label}"
    success = roll.outcome in {"success", "critical"}
    revealed: list[str] = []
    fact = db.get(Fact, roll.context.get("fact_id") or "")
    if fact and roll.total is not None:
        tiers = [(int(t[0]), str(t[1])) for t in fact.discovery.get("tiers", [])]
        if tiers:
            for statement in revealed_tiers(roll.total, tiers):
                revealed.append(statement)
        if success:
            world.reveal_fact(db, fact, to="party", actor_kind="ai", session_id=ctx.session.id)
            revealed.append(player_text(fact.statement))
            if fact.scene_id:
                _discover_secret_doors(db, fact)
    if success:
        outcome = f"ÉXITO (total {roll.total})."
        if revealed:
            outcome += " Descubre: " + " ".join(revealed)
    else:
        outcome = (f"FRACASO (total {roll.total}). No consigue su objetivo. No insinúes que había algo oculto."
                   if roll.dc is not None else f"Resultado {roll.total}.")
    text = _narrate(db, ctx, f"{action}\n{roll.label}: {outcome}\nNarra la consecuencia.", action)
    _publish_narration(db, ctx.session, text, "result", character_id=ctx.character.id, roll_id=roll.id)


def _discover_secret_doors(db: Session, fact: Fact) -> None:
    """Si el hecho corresponde a una puerta secreta del mapa de la escena, la hace visible."""
    scene = db.get(Scene, fact.scene_id) if fact.scene_id else None
    if scene is None or scene.map_id is None:
        return
    from app.models import GameMap

    game_map = db.get(GameMap, scene.map_id)
    if game_map is None:
        return
    doors = [dict(d) for d in (game_map.logic or {}).get("doors", [])]
    changed = False
    for door in doors:
        if door.get("secret") and door.get("fact_id") == fact.id and not door.get("discovered"):
            door["discovered"] = True
            changed = True
    if changed:
        game_map.logic = {**game_map.logic, "doors": doors}


# ------------------------------------------------------------- escenas ---
def schedule_scene_intro(campaign_id: str, session_id: str) -> None:
    runtime.submit(_run_safely, campaign_id, narrate_scene, session_id)


def narrate_scene(db: Session, session_id: str) -> None:
    ctx = _load(db, session_id, None)
    if ctx is None or ctx.scene is None:
        return
    text = _narrate(db, ctx, "Los personajes llegan a esta escena. Descríbela: entorno, luz, sonidos, olores, "
                             "temperatura, criaturas y objetos visibles. Después, detente.", ctx.scene.name)
    _publish_narration(db, ctx.session, text, "scene", scene_id=ctx.scene.id)


def narrate_resume(db: Session, session_id: str) -> None:
    ctx = _load(db, session_id, None)
    if ctx is None:
        return
    previous = db.scalar(select(GameSession).where(GameSession.campaign_id == ctx.session.campaign_id,
                                                    GameSession.state == "closed")
                         .order_by(GameSession.number.desc()))
    summary = previous.summary if previous else {}
    if not summary:
        return
    facts = "\n".join(f"- {line}" for line in summary.get("acontecimientos", [])[-8:])
    final = summary.get("situacion_final", "")
    text = _narrate(db, ctx, f"Resumen de la sesión anterior:\n{facts}\nSituación final: {final}\n"
                             "Escribe un breve «Anteriormente…» (3-5 frases) y recuerda dónde están "
                             "los personajes.",
                    "anteriormente")
    _publish_narration(db, ctx.session, text, "recap")


def schedule_resume(campaign_id: str, session_id: str) -> None:
    runtime.submit(_run_safely, campaign_id, narrate_resume, session_id)


# ------------------------------------------------------------- combate ---
def schedule_enemy_turn(campaign_id: str) -> None:
    from app.ai.enemy import run_enemy_turns

    runtime.submit(_run_safely, campaign_id, run_enemy_turns, campaign_id)
