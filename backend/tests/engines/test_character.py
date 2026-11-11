import pytest

from app.engines.errors import RuleViolation
from app.engines.rules.abilities import Ability, ability_modifier, level_for_xp, proficiency_bonus
from app.engines.rules.character import (
    DeathSaves,
    Sheet,
    apply_damage,
    death_save,
    heal,
    set_temp_hp,
    stabilize,
)
from app.engines.rules.conditions import Condition

SCORES = {Ability.STR: 16, Ability.DEX: 14, Ability.CON: 14, Ability.INT: 8, Ability.WIS: 12, Ability.CHA: 10}


def make(**kwargs: object) -> Sheet:
    base: dict[str, object] = {
        "name": "Thorin",
        "level": 5,
        "abilities": SCORES,
        "hp_max": 44,
        "hp_current": 44,
        "armor_class": 18,
    }
    base.update(kwargs)
    return Sheet(**base)  # type: ignore[arg-type]


def test_modificadores_y_competencia() -> None:
    assert [ability_modifier(s) for s in (1, 8, 9, 10, 11, 20, 30)] == [-5, -1, -1, 0, 0, 5, 10]
    assert [proficiency_bonus(lv) for lv in (1, 4, 5, 9, 13, 17, 20)] == [2, 2, 3, 4, 5, 6, 6]
    assert level_for_xp(0) == 1 and level_for_xp(299) == 1 and level_for_xp(300) == 2
    assert level_for_xp(355000) == 20


def test_bonificadores_de_habilidad_y_salvacion() -> None:
    sheet = make(
        skill_proficiencies=frozenset({"athletics"}),
        skill_expertise=frozenset({"perception"}),
        save_proficiencies=frozenset({Ability.STR, Ability.CON}),
    )
    assert sheet.skill_bonus("athletics") == 3 + 3
    assert sheet.skill_bonus("perception") == 1 + 6
    assert sheet.skill_bonus("stealth") == 2
    assert sheet.save_bonus(Ability.CON) == 2 + 3
    assert sheet.save_bonus(Ability.WIS) == 1
    assert sheet.passive("perception") == 17
    assert sheet.initiative_bonus == 2


def test_polivalente_suma_mitad_de_competencia() -> None:
    bard = make(jack_of_all_trades=True)
    assert bard.skill_bonus("arcana") == -1 + 1


def test_ficha_valida_datos() -> None:
    with pytest.raises(RuleViolation):
        make(hp_current=50)
    with pytest.raises(RuleViolation):
        make(level=21)


def test_danio_con_resistencia_temporales_y_vulnerabilidad() -> None:
    sheet = make(hp_temp=5, resistances=frozenset({"fire"}), vulnerabilities=frozenset({"cold"}))
    result = apply_damage(sheet, 11, "fire")
    assert result.damage_after_modifiers == 5
    assert result.absorbed_by_temp == 5
    assert result.sheet.hp_current == 44
    assert apply_damage(sheet, 10, "cold").sheet.hp_current == 44 - 15
    assert apply_damage(make(immunities=frozenset({"poison"})), 30, "poison").sheet.hp_current == 44


def test_caida_a_cero_y_muerte_instantanea() -> None:
    down = apply_damage(make(hp_current=10), 15)
    assert down.dropped_to_zero and not down.instant_death
    assert Condition.UNCONSCIOUS in down.sheet.conditions
    dead = apply_damage(make(hp_current=10), 10 + 44)
    assert dead.instant_death and dead.sheet.dead


def test_criatura_generica_muere_a_cero() -> None:
    goblin = make(name="Goblin", level=1, hp_max=7, hp_current=7, is_player_character=False)
    assert apply_damage(goblin, 7).sheet.dead


def test_danio_a_cero_suma_fallos() -> None:
    down = apply_damage(make(hp_current=1), 5).sheet
    once = apply_damage(down, 3)
    assert once.sheet.death_saves.failures == 1
    crit = apply_damage(once.sheet, 3, critical=True)
    assert crit.sheet.death_saves.failures == 3 and crit.sheet.dead


def test_salvaciones_contra_muerte() -> None:
    down = apply_damage(make(hp_current=1), 5).sheet
    s = death_save(down, 10).sheet
    s = death_save(s, 15).sheet
    third = death_save(s, 12)
    assert third.stabilized and third.sheet.stable
    assert death_save(down, 1).sheet.death_saves == DeathSaves(0, 2)
    revived = death_save(down, 20)
    assert revived.regained_consciousness and revived.sheet.hp_current == 1
    assert Condition.UNCONSCIOUS not in revived.sheet.conditions
    with pytest.raises(RuleViolation):
        death_save(make(), 10)


def test_curar_y_temporales() -> None:
    hurt = make(hp_current=10)
    assert heal(hurt, 100).hp_current == 44
    assert set_temp_hp(make(hp_temp=8), 5).hp_temp == 8
    down = apply_damage(make(hp_current=1), 5).sheet
    assert stabilize(down).stable
    with pytest.raises(RuleViolation):
        heal(hurt, -1)


def test_velocidad_con_condiciones_y_agotamiento() -> None:
    assert make(conditions=frozenset({Condition.GRAPPLED})).effective_speed_ft == 0
    assert make(exhaustion=2).effective_speed_ft == 15
    assert make(exhaustion=4).effective_hp_max == 22
