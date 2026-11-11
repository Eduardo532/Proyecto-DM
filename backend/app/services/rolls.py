"""Tiradas: el motor crea la petición, la mesa tira (digital o físico) y el motor resuelve."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.errors import RuleViolation
from app.engines.rules import dice
from app.engines.rules.abilities import SKILLS, Ability
from app.engines.rules.checks import CheckKind, CheckSpec, ModifierPart, build_check, dc_for, resolve
from app.models import Campaign, Character, DiceRoll, GameSession
from app.models.base import utc_now
from app.services.characters import to_engine
from app.services.errors import Conflict
from app.services.events import append_event


def public_roll(roll: DiceRoll) -> dict[str, Any]:
    """Vista de una tirada para la mesa: la CD solo aparece si es pública."""
    return {
        "id": roll.id,
        "character_id": roll.character_id,
        "purpose": roll.purpose,
        "label": roll.label,
        "expression": roll.expression,
        "ability": roll.ability,
        "skill": roll.skill,
        "advantage": roll.advantage,
        "status": roll.status,
        "mode": roll.mode,
        "dice": roll.dice,
        "natural": roll.natural,
        "modifiers": roll.modifiers,
        "modifier_total": sum(int(m["value"]) for m in roll.modifiers),
        "total": roll.total,
        "dc": roll.dc if roll.dc_public else None,
        "outcome": roll.outcome,
        "reason": roll.context.get("reason", ""),
    }


def pending_rolls(db: Session, campaign_id: str) -> list[DiceRoll]:
    return list(
        db.scalars(
            select(DiceRoll)
            .where(DiceRoll.campaign_id == campaign_id, DiceRoll.status == "pending")
            .order_by(DiceRoll.created_at)
        )
    )


def request_check(
    db: Session,
    session: GameSession,
    character: Character,
    *,
    kind: CheckKind,
    skill: str | None = None,
    ability: str | None = None,
    dc: int | None = None,
    difficulty: str | None = None,
    dc_public: bool = False,
    advantage: str = "none",
    reason: str = "",
    requested_by: str = "ai",
    context: dict[str, Any] | None = None,
) -> DiceRoll:
    if session.state == "closed":
        raise Conflict("La sesión está cerrada.")
    if skill is not None and skill not in SKILLS:
        raise RuleViolation(f"Habilidad desconocida: {skill}.")
    if dc is None and difficulty:
        dc = dc_for(difficulty)
    sources = [dice.Advantage(advantage)] if advantage != "none" else []
    spec = build_check(
        to_engine(character),
        kind,
        ability=Ability(ability) if ability else None,
        skill=skill,
        dc=dc,
        dc_public=dc_public,
        advantage_sources=sources,
    )
    roll = DiceRoll(
        campaign_id=session.campaign_id,
        session_id=session.id,
        character_id=character.id,
        purpose=kind.value,
        label=f"{spec.label} — {character.name}",
        expression="1d20" if spec.advantage is dice.Advantage.NONE else "2d20",
        ability=spec.ability.value,
        skill=skill,
        advantage=spec.advantage.value,
        modifiers=[{"label": p.label, "value": p.value} for p in spec.parts],
        dc=spec.dc,
        dc_public=dc_public,
        status="pending",
        requested_by=requested_by,
        context={"reason": reason, "auto_fail": spec.auto_fail, **(context or {})},
    )
    db.add(roll)
    db.flush()
    session.state = "awaiting_roll"
    append_event(db, session.campaign_id, "roll_requested", public_roll(roll), actor_kind=requested_by,
                 session_id=session.id)  # fmt: skip
    if not dc_public and dc is not None:
        append_event(db, session.campaign_id, "roll_dc", {"roll_id": roll.id, "dc": dc}, session_id=session.id,
                     visibility="dm")  # fmt: skip
    return roll


def _spec_from_roll(roll: DiceRoll) -> CheckSpec:
    return CheckSpec(
        kind=CheckKind(roll.purpose),
        ability=Ability(roll.ability or "str"),
        skill=roll.skill,
        dc=roll.dc,
        dc_public=roll.dc_public,
        advantage=dice.Advantage(roll.advantage),
        parts=tuple(ModifierPart(m["label"], int(m["value"])) for m in roll.modifiers),
        auto_fail=bool(roll.context.get("auto_fail", False)),
        label=roll.label,
    )


def resolve_check(
    db: Session, campaign: Campaign, roll: DiceRoll, mode: str, values: list[int] | None = None,
    rng: dice.RandomSource | None = None,
) -> DiceRoll:  # fmt: skip
    if roll.status != "pending":
        raise Conflict("Esta tirada ya se resolvió.")
    if campaign.dice_mode != "ask" and mode != campaign.dice_mode:
        raise RuleViolation(f"La campaña está configurada para dados en modo {campaign.dice_mode}.")
    spec = _spec_from_roll(roll)
    if mode == "manual":
        d20 = dice.D20Roll(tuple(values or ()), spec.advantage, "manual")
    elif mode == "digital":
        d20 = dice.roll_d20(spec.advantage, rng)
    else:
        raise RuleViolation("Modo de dados no válido.")
    outcome = resolve(spec, d20)
    roll.mode = mode
    roll.dice = list(d20.rolls)
    roll.natural = d20.natural
    roll.total = outcome.total
    roll.status = "resolved"
    roll.resolved_at = utc_now()
    if outcome.success is None:
        roll.outcome = None
    elif outcome.critical:
        roll.outcome = "critical"
    elif outcome.fumble:
        roll.outcome = "fumble"
    else:
        roll.outcome = "success" if outcome.success else "failure"
    roll.context = {**roll.context, "breakdown": outcome.breakdown}
    session = db.get(GameSession, roll.session_id) if roll.session_id else None
    if session and session.state == "awaiting_roll" and not pending_rolls_except(db, roll):
        session.state = "combat" if roll.context.get("combat") else "exploring"
    append_event(db, roll.campaign_id, "roll_resolved", {**public_roll(roll), "breakdown": outcome.breakdown},
                 actor_kind="player", session_id=roll.session_id)  # fmt: skip
    return roll


def pending_rolls_except(db: Session, roll: DiceRoll) -> list[DiceRoll]:
    return [r for r in pending_rolls(db, roll.campaign_id) if r.id != roll.id]


def void_roll(db: Session, roll: DiceRoll, reason: str) -> None:
    if roll.status == "void":
        return
    roll.status = "void"
    append_event(db, roll.campaign_id, "roll_voided", {"roll_id": roll.id, "reason": reason}, actor_kind="dm",
                 session_id=roll.session_id)  # fmt: skip


def free_roll(
    db: Session, campaign: Campaign, session: GameSession | None, expression: str, mode: str,
    values: list[int] | None, label: str, character_id: str | None, rng: dice.RandomSource | None = None,
) -> dict[str, Any]:  # fmt: skip
    """Tirada libre (daño, tablas, etc.). Queda registrada igual que las demás."""
    result = dice.roll_manual(expression, values or []) if mode == "manual" else dice.roll(expression, rng)
    roll = DiceRoll(
        campaign_id=campaign.id,
        session_id=session.id if session else None,
        character_id=character_id,
        purpose="custom",
        label=label or expression,
        expression=str(result.expression),
        mode=result.mode,
        dice=[v for t in result.terms for v in t.rolls],
        total=result.total,
        status="resolved",
        requested_by="player",
        resolved_at=utc_now(),
        context={"breakdown": result.describe()},
    )
    db.add(roll)
    db.flush()
    payload = {**public_roll(roll), "breakdown": result.describe()}
    append_event(db, campaign.id, "free_roll", payload, actor_kind="player",
                 session_id=session.id if session else None)  # fmt: skip
    return payload
