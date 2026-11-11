"""Pruebas de característica, habilidad, salvación, ataque e iniciativa."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.engines.errors import RuleViolation
from app.engines.rules.abilities import ABILITY_LABELS, DIFFICULTY_CLASSES, SKILLS, Ability
from app.engines.rules.character import Sheet
from app.engines.rules.conditions import auto_fail_save, roll_modifiers_from_conditions
from app.engines.rules.dice import Advantage, D20Roll, combine_advantage


class CheckKind(StrEnum):
    ABILITY = "ability"
    SKILL = "skill"
    SAVE = "save"
    ATTACK = "attack"
    INITIATIVE = "initiative"


@dataclass(frozen=True)
class ModifierPart:
    label: str
    value: int


@dataclass(frozen=True)
class CheckSpec:
    """Qué hay que tirar, contra qué y con qué modificadores. Se crea antes de la tirada."""

    kind: CheckKind
    ability: Ability
    skill: str | None
    dc: int | None
    dc_public: bool
    advantage: Advantage
    parts: tuple[ModifierPart, ...]
    auto_fail: bool = False
    label: str = ""

    @property
    def modifier(self) -> int:
        return sum(p.value for p in self.parts)


@dataclass(frozen=True)
class CheckOutcome:
    spec: CheckSpec
    roll: D20Roll
    total: int
    success: bool | None
    critical: bool = False
    fumble: bool = False
    breakdown: str = field(default="")


def dc_for(difficulty: str) -> int:
    try:
        return DIFFICULTY_CLASSES[difficulty]
    except KeyError as exc:
        raise RuleViolation(f"Dificultad desconocida: {difficulty}.") from exc


def build_check(
    sheet: Sheet,
    kind: CheckKind,
    *,
    ability: Ability | None = None,
    skill: str | None = None,
    dc: int | None = None,
    dc_public: bool = False,
    advantage_sources: list[Advantage] | None = None,
    situational: list[ModifierPart] | None = None,
    attack_bonus: int | None = None,
) -> CheckSpec:
    """Calcula el modificador y la ventaja de una prueba a partir de la ficha."""
    if dc is not None and not 1 <= dc <= 40:
        raise RuleViolation("La CD debe estar entre 1 y 40.")
    if kind is CheckKind.SKILL:
        if skill not in SKILLS:
            raise RuleViolation(f"Habilidad desconocida: {skill}.")
        ability = ability or SKILLS[skill][0]
    if kind is CheckKind.INITIATIVE:
        ability = Ability.DEX
    if ability is None:
        raise RuleViolation("Falta la característica de la prueba.")

    ability_name = ABILITY_LABELS[ability][1]
    parts: list[ModifierPart] = []
    if kind is CheckKind.SKILL and skill is not None:
        base = sheet.modifier(ability)
        parts.append(ModifierPart(ability_name, base))
        prof = sheet.skill_bonus(skill) - sheet.modifier(SKILLS[skill][0])
        if prof:
            parts.append(ModifierPart("competencia", prof))
        label = f"{SKILLS[skill][1]} ({ability_name})"
    elif kind is CheckKind.SAVE:
        parts.append(ModifierPart(ability_name, sheet.modifier(ability)))
        if ability in sheet.save_proficiencies:
            parts.append(ModifierPart("competencia", sheet.proficiency))
        label = f"Salvación de {ABILITY_LABELS[ability][0]}"
    elif kind is CheckKind.ATTACK:
        bonus = attack_bonus if attack_bonus is not None else sheet.modifier(ability) + sheet.proficiency
        parts.append(ModifierPart("ataque", bonus))
        label = "Tirada de ataque"
    elif kind is CheckKind.INITIATIVE:
        parts.append(ModifierPart(ability_name, sheet.modifier(Ability.DEX)))
        extra = sheet.initiative_bonus - sheet.modifier(Ability.DEX)
        if extra:
            parts.append(ModifierPart("rasgos", extra))
        label = "Iniciativa"
    else:
        parts.append(ModifierPart(ability_name, sheet.modifier(ability)))
        if sheet.jack_of_all_trades:
            parts.append(ModifierPart("polivalente", sheet.proficiency // 2))
        label = f"Prueba de {ABILITY_LABELS[ability][0]}"

    parts.extend(situational or [])
    sources = list(advantage_sources or [])
    sources += roll_modifiers_from_conditions(
        set(sheet.conditions), sheet.exhaustion, kind.value, ability.value
    )
    return CheckSpec(
        kind=kind,
        ability=ability,
        skill=skill,
        dc=dc,
        dc_public=dc_public,
        advantage=combine_advantage(sources),
        parts=tuple(p for p in parts if p.value or p.label == ability_name),
        auto_fail=kind is CheckKind.SAVE and auto_fail_save(set(sheet.conditions), ability.value),
        label=label,
    )


def resolve(spec: CheckSpec, roll: D20Roll) -> CheckOutcome:
    if roll.advantage is not spec.advantage:
        raise RuleViolation("La tirada no coincide con la ventaja/desventaja pedida.")
    total = roll.natural + spec.modifier
    critical = spec.kind is CheckKind.ATTACK and roll.natural == 20
    fumble = spec.kind is CheckKind.ATTACK and roll.natural == 1
    success: bool | None
    if spec.auto_fail:
        success = False
    elif spec.dc is None:
        success = None
    elif critical:
        success = True
    elif fumble:
        success = False
    else:
        success = total >= spec.dc
    parts = " ".join(f"{'+' if p.value >= 0 else '-'} {abs(p.value)} ({p.label})" for p in spec.parts)
    breakdown = f"d20 ({roll.natural}) {parts} = {total}".replace("  ", " ")
    return CheckOutcome(spec, roll, total, success, critical, fumble, breakdown)


def revealed_tiers(total: int, tiers: list[tuple[int, str]]) -> list[str]:
    """Revelación por niveles: devuelve los identificadores cuyo mínimo se alcanzó."""
    return [ident for minimum, ident in sorted(tiers) if total >= minimum]
