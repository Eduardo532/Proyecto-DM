"""Encuentros de combate persistidos: iniciativa, turnos y economía de acción."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.combat.turns import ActionKind, Combatant, EncounterTracker, TurnBudget, order_initiative
from app.engines.errors import RuleViolation
from app.engines.rules import dice
from app.engines.rules.abilities import Ability, ability_modifier
from app.models import Character, Combat, Entity, GameSession
from app.services.characters import to_engine
from app.services.errors import Conflict
from app.services.events import append_event


def active_combat(db: Session, campaign_id: str) -> Combat | None:
    return db.scalar(select(Combat).where(Combat.campaign_id == campaign_id, Combat.status == "active"))


def _tracker(combat: Combat) -> EncounterTracker:
    order = [
        Combatant(c["entity_id"], c["name"], c["initiative"], c["dex_modifier"], c["speed_ft"]) for c in combat.order
    ]
    budgets = {k: TurnBudget(**v) for k, v in combat.budgets.items()}
    return EncounterTracker(order, combat.round, combat.turn_index, budgets, set(combat.removed))


def _save(combat: Combat, tracker: EncounterTracker) -> None:
    combat.round = tracker.round
    combat.turn_index = tracker.index
    combat.budgets = {k: asdict(v) for k, v in tracker.budgets.items()}
    combat.removed = sorted(tracker.removed)


def combat_view(db: Session, combat: Combat, dm: bool) -> dict[str, Any]:
    tracker = _tracker(combat)
    order = []
    for c in combat.order:
        entity = db.get(Entity, c["entity_id"])
        if entity is None or (entity.hidden and not dm):
            continue
        public_name = entity.name if entity.kind == "character" else (entity.name_public or entity.name)
        order.append(
            {
                "entity_id": c["entity_id"],
                "name": c["name"] if dm else public_name,
                "initiative": c["initiative"],
                "kind": entity.kind,
                "disposition": entity.disposition,
                "removed": c["entity_id"] in tracker.removed,
                "budget": combat.budgets.get(c["entity_id"]),
            }
        )
    return {
        "id": combat.id,
        "status": combat.status,
        "round": combat.round,
        "current_entity_id": tracker.current.id,
        "order": order,
        "log": combat.log[-50:],
    }


def _stats(db: Session, entity: Entity) -> tuple[int, int, int]:
    """(bonificador de iniciativa, modificador de DES, velocidad) de una entidad."""
    if entity.character_id:
        character = db.get(Character, entity.character_id)
        if character:
            sheet = to_engine(character)
            return sheet.initiative_bonus, sheet.modifier(Ability.DEX), sheet.effective_speed_ft
    dex = int(entity.stats.get("dex", 10))
    speed = int(entity.stats.get("speed_ft", 30))
    return ability_modifier(dex) + int(entity.stats.get("initiative_bonus", 0)), ability_modifier(dex), speed


def start_combat(
    db: Session, session: GameSession, entity_ids: list[str], *, actor_kind: str = "ai",
    initiatives: dict[str, int] | None = None, rng: dice.RandomSource | None = None,
) -> Combat:  # fmt: skip
    """Inicia un encuentro. La iniciativa se tira en el servidor salvo que se indique."""
    if active_combat(db, session.campaign_id):
        raise Conflict("Ya hay un combate en curso.")
    if not entity_ids:
        raise RuleViolation("El combate necesita participantes.")
    combatants: list[Combatant] = []
    log: list[str] = []
    for entity_id in entity_ids:
        entity = db.get(Entity, entity_id)
        if entity is None or entity.campaign_id != session.campaign_id:
            raise RuleViolation("Una de las entidades del combate no existe.")
        bonus, dex_mod, speed = _stats(db, entity)
        if initiatives and entity_id in initiatives:
            total = initiatives[entity_id]
            log.append(f"{entity.name}: iniciativa {total} (indicada)")
        else:
            natural = dice.roll_d20(rng=rng).natural
            total = natural + bonus
            log.append(f"{entity.name}: iniciativa d20 ({natural}) {bonus:+d} = {total}")
        combatants.append(Combatant(entity.id, entity.name, total, dex_mod, speed))
    order = order_initiative(combatants, rng)
    tracker = EncounterTracker(order)
    combat = Combat(
        campaign_id=session.campaign_id,
        session_id=session.id,
        scene_id=session.scene_id,
        order=[
            {"entity_id": c.id, "name": c.name, "initiative": c.initiative, "dex_modifier": c.dex_modifier,
             "speed_ft": c.speed_ft}
            for c in order
        ],  # fmt: skip
        log=log,
    )
    _save(combat, tracker)
    db.add(combat)
    db.flush()
    session.state = "combat"
    append_event(db, session.campaign_id, "combat_started", combat_view(db, combat, dm=False), actor_kind=actor_kind,
                 session_id=session.id)  # fmt: skip
    return combat


def _require(db: Session, campaign_id: str) -> Combat:
    combat = active_combat(db, campaign_id)
    if combat is None:
        raise Conflict("No hay ningún combate en curso.")
    return combat


def next_turn(db: Session, campaign_id: str, actor_kind: str = "player") -> Combat:
    combat = _require(db, campaign_id)
    tracker = _tracker(combat)
    current = tracker.next_turn()
    _save(combat, tracker)
    combat.log = [*combat.log, f"Ronda {tracker.round}: turno de {current.name}"]
    entity = db.get(Entity, current.id)
    name = current.name if entity is None or entity.kind == "character" else (entity.name_public or entity.name)
    append_event(db, campaign_id, "combat_turn", {"round": tracker.round, "entity_id": current.id, "name": name},
                 actor_kind=actor_kind, session_id=combat.session_id)  # fmt: skip
    return combat


def spend_action(db: Session, campaign_id: str, entity_id: str, kind: str, action: str = "") -> Combat:
    combat = _require(db, campaign_id)
    tracker = _tracker(combat)
    if action == "dash":
        tracker.dash(entity_id)
    elif action == "disengage":
        tracker.disengage(entity_id)
    else:
        tracker.spend(entity_id, ActionKind(kind))
    _save(combat, tracker)
    return combat


def movement_budget(db: Session, campaign_id: str, entity_id: str, enforce_turn: bool = True) -> int | None:
    combat = active_combat(db, campaign_id)
    if combat is None:
        return None
    tracker = _tracker(combat)
    if entity_id not in tracker.budgets:
        return None
    if enforce_turn:
        tracker.require_turn(entity_id)
    return tracker.budgets[entity_id].movement_ft


def spend_movement(db: Session, campaign_id: str, entity_id: str, cost_ft: int) -> None:
    combat = active_combat(db, campaign_id)
    if combat is None:
        return
    tracker = _tracker(combat)
    if entity_id in tracker.budgets:
        budget = tracker.budgets[entity_id]
        tracker.budgets[entity_id] = TurnBudget(budget.action, budget.bonus, budget.reaction,
                                                max(0, budget.movement_ft - cost_ft), budget.dashed,
                                                budget.disengaged)  # fmt: skip
        _save(combat, tracker)


def remove_combatant(db: Session, campaign_id: str, entity_id: str) -> None:
    combat = active_combat(db, campaign_id)
    if combat is None:
        return
    tracker = _tracker(combat)
    if entity_id in tracker.budgets and entity_id not in tracker.removed:
        try:
            tracker.remove(entity_id)
        except RuleViolation:
            return
        _save(combat, tracker)


def end_combat(db: Session, campaign_id: str, actor_kind: str = "dm") -> Combat:
    combat = _require(db, campaign_id)
    combat.status = "ended"
    session = db.get(GameSession, combat.session_id) if combat.session_id else None
    if session and session.state == "combat":
        session.state = "exploring"
    append_event(db, campaign_id, "combat_ended", {"round": combat.round}, actor_kind=actor_kind,
                 session_id=combat.session_id)  # fmt: skip
    return combat
