"""Turnos de los enemigos: el motor calcula las opciones legales y una táctica sencilla decide.

Táctica rápida (sin modelo, para que el combate no dependa de la velocidad del modelo):
- Si la criatura tiene menos de un cuarto de sus PG y no es temeraria, intenta alejarse.
- Si no, se acerca al personaje visible más cercano y le ataca si queda adyacente.
El modelo solo pone la narración, si está disponible.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import LLMUnavailable
from app.ai.prompts import SYSTEM_NARRATOR
from app.ai.runtime import runtime
from app.engines.errors import RuleViolation
from app.engines.maps.grid import Occupancy, cell_label, reachable
from app.engines.rules import dice
from app.models import Character, Entity, GameMap
from app.services import combat as combat_service
from app.services import world
from app.services.characters import change_hp
from app.services.events import append_event

log = logging.getLogger("vdm.ai")


def _is_ai_controlled(entity: Entity | None) -> bool:
    return entity is not None and entity.kind != "character" and entity.disposition == "hostile"


def run_enemy_turns(db: Session, campaign_id: str) -> None:
    for _ in range(20):
        combat = combat_service.active_combat(db, campaign_id)
        if combat is None:
            return
        view = combat_service.combat_view(db, combat, dm=True)
        entity = db.get(Entity, view["current_entity_id"])
        if not _is_ai_controlled(entity):
            return
        assert entity is not None
        lines = _act(db, combat.session_id, entity)
        text = _narrate(lines)
        append_event(db, campaign_id, "narration", {"text": text, "kind": "combat", "speaker": entity.name_public
                     or entity.name}, actor_kind="ai", session_id=combat.session_id)
        if not _party_standing(db, campaign_id):
            combat_service.end_combat(db, campaign_id, actor_kind="ai")
            return
        combat_service.next_turn(db, campaign_id, actor_kind="ai")
        db.flush()


def _party_standing(db: Session, campaign_id: str) -> bool:
    return any(c.hp_current > 0 for c in db.scalars(select(Character).where(Character.campaign_id == campaign_id,
                                                                             Character.status == "active")))


def _act(db: Session, session_id: str | None, entity: Entity) -> list[str]:
    name = entity.name_public or entity.name
    if entity.hp_current is not None and entity.hp_current <= 0:
        combat_service.remove_combatant(db, entity.campaign_id, entity.id)
        return [f"{name} yace inmóvil."]
    game_map = db.get(GameMap, entity.map_id) if entity.map_id else None
    targets = [e for e in db.scalars(select(Entity).where(Entity.map_id == entity.map_id, Entity.kind == "character"))
               if e.x is not None and e.y is not None and _alive(db, e)]
    if game_map is None or entity.x is None or entity.y is None or not targets:
        return [f"{name} espera, atento."]
    grid = world.grid_for(game_map)
    here = (entity.x, entity.y)
    target = min(targets, key=lambda t: grid.distance_ft(here, (t.x, t.y)))  # type: ignore[arg-type]
    target_cell = (int(target.x), int(target.y))  # type: ignore[arg-type]
    lines: list[str] = []
    cowardly = entity.hp_current is not None and entity.hp_max and entity.hp_current < entity.hp_max / 4 \
        and not entity.stats.get("fearless")
    budget = combat_service.movement_budget(db, entity.campaign_id, entity.id, enforce_turn=False) or 0
    others = db.scalars(select(Entity).where(Entity.map_id == entity.map_id, Entity.id != entity.id))
    occupied = frozenset((o.x, o.y) for o in others if o.x is not None and o.y is not None)
    options = reachable(grid, here, budget, Occupancy(hostile=occupied))
    if cowardly:
        best = max(options, key=lambda c: grid.distance_ft(c, target_cell))
        if best != here:
            world.move_entity(db, entity, best[0], best[1], actor_kind="ai", session_id=session_id)
            combat_service.spend_movement(db, entity.campaign_id, entity.id, options[best])
            lines.append(f"{name}, malherido, retrocede hasta {cell_label(best)}.")
        return lines or [f"{name} busca una salida, acorralado."]
    if grid.distance_ft(here, target_cell) > grid.cell_size_ft:
        adjacent = [c for c in options if grid.distance_ft(c, target_cell) == grid.cell_size_ft]
        destination = min(adjacent or options, key=lambda c: (grid.distance_ft(c, target_cell), options[c]))
        if destination != here:
            try:
                world.move_entity(db, entity, destination[0], destination[1], actor_kind="ai", session_id=session_id)
                combat_service.spend_movement(db, entity.campaign_id, entity.id, options[destination])
                lines.append(f"{name} avanza hasta {cell_label(destination)}.")
            except RuleViolation as exc:
                log.info("Movimiento enemigo rechazado: %s", exc)
    if entity.x is not None and entity.y is not None and grid.distance_ft((entity.x, entity.y), target_cell) <= 5:
        lines.append(_attack(db, session_id, entity, target))
    elif not lines:
        lines.append(f"{name} no puede alcanzar a nadie.")
    return lines


def _alive(db: Session, entity: Entity) -> bool:
    character = db.get(Character, entity.character_id) if entity.character_id else None
    return character is not None and character.status == "active" and character.hp_current > 0


def _attack(db: Session, session_id: str | None, attacker: Entity, target: Entity) -> str:
    name = attacker.name_public or attacker.name
    character = db.get(Character, target.character_id) if target.character_id else None
    if character is None:
        return f"{name} duda."
    bonus = int(attacker.stats.get("attack_bonus", 3))
    damage_expr = str(attacker.stats.get("damage", "1d6+1"))
    damage_type = str(attacker.stats.get("damage_type", "slashing"))
    attack_name = str(attacker.stats.get("attack_name", "ataque"))
    combat_service.spend_action(db, attacker.campaign_id, attacker.id, "action")
    d20 = dice.roll_d20()
    total = d20.natural + bonus
    hit = d20.natural == 20 or (d20.natural != 1 and total >= character.armor_class)
    detail = f"{attack_name}: d20 ({d20.natural}) {bonus:+d} = {total} contra CA {character.armor_class}"
    append_event(db, attacker.campaign_id, "enemy_attack", {"attacker": name, "target": character.name,
                 "detail": detail, "hit": hit}, actor_kind="ai", session_id=session_id)
    if not hit:
        return f"{name} ataca a {character.name} con su {attack_name}, pero falla ({total})."
    expression = dice.parse(damage_expr)
    if d20.natural == 20:
        expression = dice.critical_damage(expression)
    damage = max(0, dice.roll(expression).total)
    result = change_hp(db, character, "damage", damage, damage_type=damage_type, critical=d20.natural == 20,
                       reason=f"{attack_name} de {name}", session_id=session_id, actor_kind="ai")
    text = f"{name} golpea a {character.name} con su {attack_name}: {result['damage']} de daño"
    if result.get("dropped_to_zero"):
        text += f". {character.name} cae al suelo"
    return text + "."


def _narrate(lines: list[str]) -> str:
    plain = " ".join(lines)
    try:
        return runtime.provider.chat([
            {"role": "system", "content": SYSTEM_NARRATOR},
            {"role": "user", "content": "Narra en 1-3 frases estos hechos de combate ya resueltos, sin cambiar "
                                        f"ningún número ni resultado:\n{plain}"},
        ]).strip() or plain
    except LLMUnavailable:
        return plain
