from app.engines.rules.abilities import Ability
from app.engines.rules.character import Sheet
from app.engines.rules.checks import CheckKind, build_check, dc_for, resolve, revealed_tiers
from app.engines.rules.conditions import Condition
from app.engines.rules.dice import Advantage, D20Roll

SCORES = {Ability.STR: 10, Ability.DEX: 16, Ability.CON: 12, Ability.INT: 14, Ability.WIS: 10, Ability.CHA: 8}


def rogue(**kwargs: object) -> Sheet:
    base: dict[str, object] = {
        "name": "Lyra",
        "level": 3,
        "abilities": SCORES,
        "hp_max": 21,
        "hp_current": 21,
        "armor_class": 14,
        "skill_proficiencies": frozenset({"investigation", "stealth"}),
        "save_proficiencies": frozenset({Ability.DEX, Ability.INT}),
    }
    base.update(kwargs)
    return Sheet(**base)  # type: ignore[arg-type]


def test_prueba_de_habilidad_con_cd_oculta() -> None:
    spec = build_check(rogue(), CheckKind.SKILL, skill="investigation", dc=dc_for("media"))
    assert spec.modifier == 2 + 2
    assert spec.dc == 15 and not spec.dc_public
    outcome = resolve(spec, D20Roll((11,), Advantage.NONE))
    assert outcome.total == 15 and outcome.success is True
    assert "d20 (11)" in outcome.breakdown


def test_envenenado_impone_desventaja_en_pruebas() -> None:
    spec = build_check(rogue(conditions=frozenset({Condition.POISONED})), CheckKind.SKILL, skill="stealth")
    assert spec.advantage is Advantage.DISADVANTAGE


def test_ventaja_externa_y_desventaja_se_anulan() -> None:
    sheet = rogue(conditions=frozenset({Condition.POISONED}))
    spec = build_check(sheet, CheckKind.SKILL, skill="stealth", advantage_sources=[Advantage.ADVANTAGE])
    assert spec.advantage is Advantage.NONE


def test_paralizado_falla_salvacion_de_destreza() -> None:
    spec = build_check(rogue(conditions=frozenset({Condition.PARALYZED})), CheckKind.SAVE, ability=Ability.DEX, dc=10)
    assert resolve(spec, D20Roll((20,), Advantage.NONE)).success is False


def test_ataque_critico_y_pifia() -> None:
    spec = build_check(rogue(), CheckKind.ATTACK, ability=Ability.DEX, dc=30)
    assert resolve(spec, D20Roll((20,), Advantage.NONE)).critical
    assert resolve(spec, D20Roll((20,), Advantage.NONE)).success is True
    assert resolve(spec, D20Roll((1,), Advantage.NONE)).success is False


def test_salvacion_con_competencia() -> None:
    spec = build_check(rogue(), CheckKind.SAVE, ability=Ability.INT, dc=13)
    assert spec.modifier == 2 + 2


def test_revelacion_por_niveles() -> None:
    tiers = [(15, "inscripcion"), (10, "libro"), (20, "autor")]
    assert revealed_tiers(9, tiers) == []
    assert revealed_tiers(16, tiers) == ["libro", "inscripcion"]
