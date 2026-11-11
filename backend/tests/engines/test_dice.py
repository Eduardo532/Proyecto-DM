import pytest

from app.engines.errors import RuleViolation
from app.engines.rules.dice import (
    Advantage,
    D20Roll,
    combine_advantage,
    critical_damage,
    parse,
    roll,
    roll_d20,
    roll_manual,
    seeded_random,
)


def test_parse_y_representacion() -> None:
    expr = parse("2d6 + 1d8 - 3")
    assert expr.dice_count == 3
    assert expr.modifier == -3
    assert str(expr) == "2d6+1d8-3"
    assert str(parse("4d6kh3")) == "4d6kh3"
    assert parse("d20").terms[0].count == 1


@pytest.mark.parametrize("bad", ["", "2d7", "3x6", "2d6 3", "0d6", "2d6kh3", "101d6"])
def test_parse_rechaza_expresiones_invalidas(bad: str) -> None:
    with pytest.raises(RuleViolation):
        parse(bad)


def test_tiradas_dentro_de_rango_y_total() -> None:
    rng = seeded_random(1)
    for _ in range(200):
        result = roll("3d6+2", rng)
        rolls = result.terms[0].rolls
        assert all(1 <= r <= 6 for r in rolls)
        assert result.total == sum(rolls) + 2


def test_conservar_mayores() -> None:
    result = roll_manual("4d6kh3", [1, 6, 3, 5])
    assert result.terms[0].kept == (6, 5, 3)
    assert result.total == 14
    assert result.mode == "manual"


def test_tirada_manual_valida_cantidad_y_rango() -> None:
    with pytest.raises(RuleViolation):
        roll_manual("2d6", [3])
    with pytest.raises(RuleViolation):
        roll_manual("1d6", [7])


def test_ventaja_y_desventaja() -> None:
    assert D20Roll((4, 17), Advantage.ADVANTAGE).natural == 17
    assert D20Roll((4, 17), Advantage.DISADVANTAGE).natural == 4
    assert D20Roll((9,), Advantage.NONE).natural == 9
    with pytest.raises(RuleViolation):
        D20Roll((9,), Advantage.ADVANTAGE)
    assert len(roll_d20(Advantage.ADVANTAGE, seeded_random(3)).rolls) == 2


def test_ventaja_y_desventaja_se_anulan_sin_acumular() -> None:
    adv, dis = Advantage.ADVANTAGE, Advantage.DISADVANTAGE
    assert combine_advantage([adv, adv, dis]) is Advantage.NONE
    assert combine_advantage([adv, adv]) is Advantage.ADVANTAGE
    assert combine_advantage([]) is Advantage.NONE


def test_critico_duplica_dados_no_modificador() -> None:
    assert str(critical_damage(parse("1d8+2d6+3"))) == "2d8+4d6+3"
