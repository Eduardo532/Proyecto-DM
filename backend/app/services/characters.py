"""Fichas: conversión al motor de reglas, valores derivados y cambios validados con historial."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.engines.errors import RuleViolation
from app.engines.rules import character as rules
from app.engines.rules.abilities import SKILLS, Ability, ability_modifier
from app.engines.rules.conditions import Condition
from app.models import Character, CharacterChange
from app.schemas.character import Derived, SheetData
from app.services.events import append_event


def sheet_data(character: Character) -> SheetData:
    return SheetData.model_validate(character.sheet or {})


def to_engine(character: Character) -> rules.Sheet:
    data = sheet_data(character)
    return rules.Sheet(
        name=character.name,
        level=character.level,
        abilities={Ability(k): v for k, v in data.abilities.items()},
        hp_max=character.hp_max,
        hp_current=character.hp_current,
        hp_temp=character.hp_temp,
        armor_class=character.armor_class,
        speed_ft=character.speed_ft,
        skill_proficiencies=frozenset(data.skill_proficiencies),
        skill_expertise=frozenset(data.skill_expertise),
        save_proficiencies=frozenset(Ability(a) for a in data.save_proficiencies),
        jack_of_all_trades=data.jack_of_all_trades,
        initiative_bonus_extra=data.initiative_bonus_extra,
        resistances=frozenset(data.resistances),
        immunities=frozenset(data.immunities),
        vulnerabilities=frozenset(data.vulnerabilities),
        conditions=frozenset(Condition(c) for c in character.conditions if c in Condition._value2member_map_),
        exhaustion=character.exhaustion,
        darkvision_ft=data.darkvision_ft,
        death_saves=rules.DeathSaves(
            character.death_saves.get("successes", 0), character.death_saves.get("failures", 0)
        ),
        stable=character.stable,
        dead=character.status == "dead",
    )


def derived(character: Character) -> Derived:
    sheet = to_engine(character)
    data = sheet_data(character)
    spell_dc = spell_attack = None
    if data.spellcasting_ability in {a.value for a in Ability}:
        mod = sheet.modifier(Ability(str(data.spellcasting_ability)))
        spell_dc = 8 + sheet.proficiency + mod
        spell_attack = sheet.proficiency + mod
    attacks: list[dict[str, str | int]] = []
    for attack in data.attacks:
        mod = ability_modifier(data.abilities[attack.ability])
        bonus = mod + (sheet.proficiency if attack.proficient else 0) + attack.attack_bonus_extra
        damage = attack.damage + (f"{mod:+d}" if mod else "")
        attacks.append({"name": attack.name, "bonus": bonus, "damage": damage, "damage_type": attack.damage_type})
    return Derived(
        proficiency_bonus=sheet.proficiency,
        ability_modifiers={a.value: sheet.modifier(a) for a in Ability},
        skills={s: sheet.skill_bonus(s) for s in SKILLS},
        saves={a.value: sheet.save_bonus(a) for a in Ability},
        initiative=sheet.initiative_bonus,
        passive_perception=sheet.passive("perception"),
        passive_investigation=sheet.passive("investigation"),
        passive_insight=sheet.passive("insight"),
        spell_save_dc=spell_dc,
        spell_attack_bonus=spell_attack,
        attacks=attacks,
    )


TRACKED = ("hp_current", "hp_temp", "conditions", "death_saves", "stable", "status")


def _snapshot(character: Character) -> dict[str, Any]:
    return {f: getattr(character, f) for f in TRACKED}


def _apply_engine(character: Character, sheet: rules.Sheet) -> None:
    character.hp_current = sheet.hp_current
    character.hp_temp = sheet.hp_temp
    character.conditions = sorted(c.value for c in sheet.conditions)
    character.death_saves = {"successes": sheet.death_saves.successes, "failures": sheet.death_saves.failures}
    character.stable = sheet.stable
    if sheet.dead:
        character.status = "dead"


def record_changes(
    db: Session,
    character: Character,
    before: dict[str, Any],
    reason: str,
    *,
    session_id: str | None,
    actor_kind: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    after = _snapshot(character)
    changed = {k: (before[k], after[k]) for k in TRACKED if before[k] != after[k]}
    character.version += 1
    event = append_event(
        db,
        character.campaign_id,
        event_type,
        {**payload, "character_id": character.id, "name": character.name,
         "changes": {k: v[1] for k, v in changed.items()}},
        actor_kind=actor_kind,
        session_id=session_id,
    )
    for field_name, (old, new) in changed.items():
        db.add(
            CharacterChange(
                character_id=character.id, event_id=event.id, field=field_name, before=old, after=new, reason=reason
            )
        )


def change_hp(
    db: Session,
    character: Character,
    kind: str,
    amount: int,
    *,
    damage_type: str = "",
    critical: bool = False,
    reason: str = "",
    session_id: str | None = None,
    actor_kind: str = "dm",
) -> dict[str, Any]:
    before = _snapshot(character)
    sheet = to_engine(character)
    details: dict[str, Any] = {"kind": kind, "amount": amount}
    if kind == "damage":
        result = rules.apply_damage(sheet, amount, damage_type, critical)
        _apply_engine(character, result.sheet)
        details.update(
            damage=result.damage_after_modifiers,
            absorbed_by_temp=result.absorbed_by_temp,
            dropped_to_zero=result.dropped_to_zero,
            instant_death=result.instant_death,
            damage_type=damage_type,
        )
    elif kind == "heal":
        _apply_engine(character, rules.heal(sheet, amount))
    elif kind == "temp":
        _apply_engine(character, rules.set_temp_hp(sheet, amount))
    else:
        raise RuleViolation("Tipo de cambio de PG no válido.")
    record_changes(
        db, character, before, reason or kind, session_id=session_id, actor_kind=actor_kind,
        event_type="character_hp", payload=details,
    )
    return details


def set_condition(
    db: Session, character: Character, condition: str, present: bool, *, session_id: str | None = None,
    actor_kind: str = "dm",
) -> None:
    if condition not in Condition._value2member_map_ and condition != "exhaustion":
        raise RuleViolation(f"Condición desconocida: {condition}.")
    before = _snapshot(character)
    current = set(character.conditions)
    if present:
        current.add(condition)
    else:
        current.discard(condition)
    character.conditions = sorted(current)
    record_changes(
        db, character, before, f"condición {condition}", session_id=session_id, actor_kind=actor_kind,
        event_type="character_condition", payload={"condition": condition, "present": present},
    )


def death_save(db: Session, character: Character, natural: int, *, session_id: str | None = None) -> dict[str, Any]:
    before = _snapshot(character)
    result = rules.death_save(to_engine(character), natural)
    _apply_engine(character, result.sheet)
    details = {
        "natural": natural,
        "success": result.success,
        "stabilized": result.stabilized,
        "died": result.died,
        "regained_consciousness": result.regained_consciousness,
    }
    record_changes(
        db, character, before, "salvación contra muerte", session_id=session_id, actor_kind="system",
        event_type="death_save", payload=details,
    )
    return details
