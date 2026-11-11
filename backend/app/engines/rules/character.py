"""Ficha de personaje: valores derivados y operaciones validadas sobre los puntos de golpe."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.engines.errors import RuleViolation
from app.engines.rules.abilities import SKILLS, Ability, ability_modifier, proficiency_bonus
from app.engines.rules.conditions import SPEED_ZERO, Condition


@dataclass(frozen=True)
class DeathSaves:
    successes: int = 0
    failures: int = 0


@dataclass(frozen=True)
class Sheet:
    """Datos mecánicos de una criatura (personaje o PNJ) necesarios para el motor."""

    name: str
    level: int
    abilities: dict[Ability, int]
    hp_max: int
    hp_current: int
    armor_class: int
    speed_ft: int = 30
    hp_temp: int = 0
    skill_proficiencies: frozenset[str] = frozenset()
    skill_expertise: frozenset[str] = frozenset()
    save_proficiencies: frozenset[Ability] = frozenset()
    jack_of_all_trades: bool = False
    initiative_bonus_extra: int = 0
    resistances: frozenset[str] = frozenset()
    immunities: frozenset[str] = frozenset()
    vulnerabilities: frozenset[str] = frozenset()
    conditions: frozenset[Condition] = frozenset()
    exhaustion: int = 0
    darkvision_ft: int = 0
    death_saves: DeathSaves = field(default_factory=DeathSaves)
    stable: bool = False
    dead: bool = False
    is_player_character: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.level <= 20:
            raise RuleViolation("El nivel debe estar entre 1 y 20.")
        if self.hp_max < 1:
            raise RuleViolation("Los puntos de golpe máximos deben ser al menos 1.")
        if not 0 <= self.hp_current <= self.hp_max:
            raise RuleViolation("Los puntos de golpe actuales deben estar entre 0 y el máximo.")
        if self.hp_temp < 0:
            raise RuleViolation("Los puntos de golpe temporales no pueden ser negativos.")
        if not 0 <= self.exhaustion <= 6:
            raise RuleViolation("El agotamiento va de 0 a 6.")
        for ability in Ability:
            score = self.abilities.get(ability)
            if score is None or not 1 <= score <= 30:
                raise RuleViolation(f"Puntuación de {ability.value} no válida.")

    # ---- valores derivados -------------------------------------------------
    @property
    def proficiency(self) -> int:
        return proficiency_bonus(self.level)

    def modifier(self, ability: Ability) -> int:
        return ability_modifier(self.abilities[ability])

    def skill_bonus(self, skill: str) -> int:
        if skill not in SKILLS:
            raise RuleViolation(f"Habilidad desconocida: {skill}.")
        bonus = self.modifier(SKILLS[skill][0])
        if skill in self.skill_expertise:
            bonus += 2 * self.proficiency
        elif skill in self.skill_proficiencies:
            bonus += self.proficiency
        elif self.jack_of_all_trades:
            bonus += self.proficiency // 2
        return bonus

    def save_bonus(self, ability: Ability) -> int:
        bonus = self.modifier(ability)
        if ability in self.save_proficiencies:
            bonus += self.proficiency
        return bonus

    def ability_check_bonus(self, ability: Ability) -> int:
        bonus = self.modifier(ability)
        if self.jack_of_all_trades:
            bonus += self.proficiency // 2
        return bonus

    @property
    def initiative_bonus(self) -> int:
        return self.ability_check_bonus(Ability.DEX) + self.initiative_bonus_extra

    def passive(self, skill: str, advantage: int = 0) -> int:
        """Puntuación pasiva: 10 + bonificador, ±5 por ventaja (1) o desventaja (-1)."""
        return 10 + self.skill_bonus(skill) + 5 * advantage

    @property
    def is_conscious(self) -> bool:
        return self.hp_current > 0 and not self.dead

    @property
    def effective_speed_ft(self) -> int:
        if self.conditions & SPEED_ZERO or self.exhaustion >= 5:
            return 0
        speed = self.speed_ft
        if self.exhaustion >= 2:
            speed //= 2
        return speed

    @property
    def effective_hp_max(self) -> int:
        """Agotamiento 4+: los PG máximos se reducen a la mitad."""
        return self.hp_max // 2 if self.exhaustion >= 4 else self.hp_max


@dataclass(frozen=True)
class DamageResult:
    sheet: Sheet
    damage_after_modifiers: int
    absorbed_by_temp: int
    hp_lost: int
    dropped_to_zero: bool
    instant_death: bool
    death_save_failures_added: int


def apply_damage(sheet: Sheet, amount: int, damage_type: str = "", critical: bool = False) -> DamageResult:
    """Aplica daño con inmunidad, resistencia, vulnerabilidad, PG temporales y caída a 0."""
    if amount < 0:
        raise RuleViolation("El daño no puede ser negativo.")
    if sheet.dead:
        raise RuleViolation(f"{sheet.name} ya está muerto.")
    damage = amount
    if damage_type in sheet.immunities:
        damage = 0
    else:
        if damage_type in sheet.resistances:
            damage //= 2
        if damage_type in sheet.vulnerabilities:
            damage *= 2

    absorbed = min(sheet.hp_temp, damage)
    remaining = damage - absorbed
    new_temp = sheet.hp_temp - absorbed

    if sheet.hp_current == 0:
        # Daño estando a 0 PG: fallos de salvación contra muerte (2 si es crítico).
        if remaining == 0:
            return DamageResult(replace(sheet, hp_temp=new_temp), damage, absorbed, 0, False, False, 0)
        if remaining >= sheet.hp_max:
            dead_sheet = replace(sheet, hp_temp=new_temp, dead=True, stable=False)
            return DamageResult(dead_sheet, damage, absorbed, 0, False, True, 0)
        added = 2 if critical else 1
        failures = min(3, sheet.death_saves.failures + added)
        updated = replace(
            sheet,
            hp_temp=new_temp,
            stable=False,
            death_saves=DeathSaves(sheet.death_saves.successes, failures),
            dead=failures >= 3,
        )
        return DamageResult(updated, damage, absorbed, 0, False, False, added)

    hp_lost = min(sheet.hp_current, remaining)
    overflow = remaining - hp_lost
    new_hp = sheet.hp_current - hp_lost
    dropped = new_hp == 0 and hp_lost > 0
    instant_death = dropped and overflow >= sheet.hp_max
    conditions = set(sheet.conditions)
    dead = instant_death
    if dropped and not instant_death:
        if sheet.is_player_character:
            conditions.update({Condition.UNCONSCIOUS, Condition.PRONE})
        else:
            dead = True  # criaturas genéricas mueren al llegar a 0 (DMG 2014)
    updated = replace(
        sheet,
        hp_current=new_hp,
        hp_temp=new_temp,
        conditions=frozenset(conditions),
        dead=dead,
        stable=False,
        death_saves=DeathSaves() if dropped else sheet.death_saves,
    )
    return DamageResult(updated, damage, absorbed, hp_lost, dropped, instant_death, 0)


def heal(sheet: Sheet, amount: int) -> Sheet:
    if amount < 0:
        raise RuleViolation("La curación no puede ser negativa.")
    if sheet.dead:
        raise RuleViolation(f"{sheet.name} está muerto y no puede curarse así.")
    if amount == 0:
        return sheet
    new_hp = min(sheet.effective_hp_max, sheet.hp_current + amount)
    conditions = set(sheet.conditions)
    if sheet.hp_current == 0 and new_hp > 0:
        conditions.discard(Condition.UNCONSCIOUS)
    return replace(
        sheet,
        hp_current=new_hp,
        conditions=frozenset(conditions),
        death_saves=DeathSaves(),
        stable=False,
    )


def set_temp_hp(sheet: Sheet, amount: int) -> Sheet:
    """Los PG temporales no se acumulan: se conserva el valor mayor."""
    if amount < 0:
        raise RuleViolation("Los PG temporales no pueden ser negativos.")
    return replace(sheet, hp_temp=max(sheet.hp_temp, amount))


@dataclass(frozen=True)
class DeathSaveResult:
    sheet: Sheet
    success: bool
    regained_consciousness: bool
    stabilized: bool
    died: bool


def death_save(sheet: Sheet, natural: int) -> DeathSaveResult:
    if sheet.hp_current > 0 or sheet.dead or sheet.stable:
        raise RuleViolation(f"{sheet.name} no necesita tirar salvaciones contra muerte.")
    if not 1 <= natural <= 20:
        raise RuleViolation("El resultado del d20 debe estar entre 1 y 20.")
    if natural == 20:
        healed = heal(sheet, 1)
        return DeathSaveResult(healed, True, True, False, False)
    saves = sheet.death_saves
    if natural == 1:
        saves = DeathSaves(saves.successes, min(3, saves.failures + 2))
    elif natural >= 10:
        saves = DeathSaves(saves.successes + 1, saves.failures)
    else:
        saves = DeathSaves(saves.successes, saves.failures + 1)
    died = saves.failures >= 3
    stabilized = saves.successes >= 3 and not died
    updated = replace(
        sheet,
        death_saves=DeathSaves() if stabilized else saves,
        stable=stabilized,
        dead=died,
    )
    return DeathSaveResult(updated, natural >= 10, False, stabilized, died)


def stabilize(sheet: Sheet) -> Sheet:
    """Estabilizar (Medicina CD 10 superada o efecto equivalente)."""
    if sheet.hp_current > 0 or sheet.dead:
        raise RuleViolation(f"{sheet.name} no está moribundo.")
    return replace(sheet, stable=True, death_saves=DeathSaves())
