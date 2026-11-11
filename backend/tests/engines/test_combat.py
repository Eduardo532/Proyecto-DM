import pytest

from app.engines.combat.turns import (
    ActionKind,
    Combatant,
    EncounterTracker,
    order_initiative,
    provokes_opportunity_attack,
)
from app.engines.errors import RuleViolation
from app.engines.rules.dice import seeded_random


def combatants() -> list[Combatant]:
    return [
        Combatant("a", "Thorin", 12, 1, 25),
        Combatant("b", "Goblin", 18, 2, 30),
        Combatant("c", "Lyra", 12, 3, 30),
    ]


def test_orden_de_iniciativa_con_desempate_por_destreza() -> None:
    order = order_initiative(combatants(), seeded_random(0))
    assert [c.name for c in order] == ["Goblin", "Lyra", "Thorin"]


def test_economia_de_accion_y_turnos() -> None:
    tracker = EncounterTracker(order_initiative(combatants(), seeded_random(0)))
    assert tracker.current.name == "Goblin"
    tracker.spend("b", ActionKind.ACTION)
    with pytest.raises(RuleViolation):
        tracker.spend("b", ActionKind.ACTION)
    with pytest.raises(RuleViolation):
        tracker.spend("a", ActionKind.ACTION)
    tracker.spend("a", ActionKind.REACTION)  # las reacciones no requieren su turno
    tracker.move("b", 30)
    with pytest.raises(RuleViolation):
        tracker.move("b", 5)
    tracker.next_turn()
    tracker.dash("c")
    assert tracker.budgets["c"].movement_ft == 60
    tracker.next_turn()
    tracker.next_turn()
    assert tracker.round == 2 and tracker.current.name == "Goblin"
    assert tracker.budgets["b"].action


def test_retirar_combatiente() -> None:
    tracker = EncounterTracker(order_initiative(combatants(), seeded_random(0)))
    tracker.remove("b")
    assert tracker.current.name == "Lyra"


def test_ataque_de_oportunidad() -> None:
    assert provokes_opportunity_attack(True, False, False)
    assert not provokes_opportunity_attack(True, False, True)
    assert not provokes_opportunity_attack(False, False, False)
