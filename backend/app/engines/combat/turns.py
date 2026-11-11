"""Orden de iniciativa y economía de acción."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from app.engines.errors import RuleViolation
from app.engines.rules.dice import RandomSource, system_random


class ActionKind(StrEnum):
    ACTION = "action"
    BONUS = "bonus"
    REACTION = "reaction"


ACTION_LABELS = {
    ActionKind.ACTION: "acción",
    ActionKind.BONUS: "acción adicional",
    ActionKind.REACTION: "reacción",
}

STANDARD_ACTIONS: dict[str, str] = {
    "attack": "Atacar",
    "cast": "Lanzar un conjuro",
    "dash": "Correr",
    "disengage": "Retirarse",
    "dodge": "Esquivar",
    "help": "Ayudar",
    "hide": "Esconderse",
    "ready": "Preparar",
    "search": "Buscar",
    "use_object": "Usar un objeto",
}


@dataclass(frozen=True)
class Combatant:
    id: str
    name: str
    initiative: int
    dex_modifier: int
    speed_ft: int
    tiebreak: float = 0.0


@dataclass(frozen=True)
class TurnBudget:
    action: bool = True
    bonus: bool = True
    reaction: bool = True
    movement_ft: int = 0
    dashed: bool = False
    disengaged: bool = False

    def spend(self, kind: ActionKind) -> TurnBudget:
        available = {
            ActionKind.ACTION: self.action,
            ActionKind.BONUS: self.bonus,
            ActionKind.REACTION: self.reaction,
        }[kind]
        if not available:
            raise RuleViolation(f"Ya se usó la {ACTION_LABELS[kind]} en este turno.")
        if kind is ActionKind.ACTION:
            return replace(self, action=False)
        if kind is ActionKind.BONUS:
            return replace(self, bonus=False)
        return replace(self, reaction=False)

    def move(self, cost_ft: int) -> TurnBudget:
        if cost_ft < 0:
            raise RuleViolation("El coste de movimiento no puede ser negativo.")
        if cost_ft > self.movement_ft:
            raise RuleViolation(
                f"No hay movimiento suficiente: quedan {self.movement_ft} pies y se necesitan {cost_ft}."
            )
        return replace(self, movement_ft=self.movement_ft - cost_ft)


def order_initiative(combatants: list[Combatant], rng: RandomSource | None = None) -> list[Combatant]:
    """Mayor iniciativa primero; empate: mayor Destreza; si persiste, al azar."""
    source = rng or system_random()
    with_tiebreak = [replace(c, tiebreak=source.randint(0, 10**6) / 10**6) for c in combatants]
    return sorted(with_tiebreak, key=lambda c: (-c.initiative, -c.dex_modifier, -c.tiebreak))


@dataclass
class EncounterTracker:
    order: list[Combatant]
    round: int = 1
    index: int = 0
    budgets: dict[str, TurnBudget] = field(default_factory=dict)
    removed: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.order:
            raise RuleViolation("Un encuentro necesita al menos un combatiente.")
        for combatant in self.order:
            self.budgets.setdefault(combatant.id, TurnBudget(movement_ft=combatant.speed_ft))

    @property
    def current(self) -> Combatant:
        return self.order[self.index]

    def require_turn(self, combatant_id: str) -> None:
        if combatant_id != self.current.id:
            raise RuleViolation(f"No es su turno: ahora actúa {self.current.name}.")

    def spend(self, combatant_id: str, kind: ActionKind) -> None:
        if kind is not ActionKind.REACTION:
            self.require_turn(combatant_id)
        self.budgets[combatant_id] = self.budgets[combatant_id].spend(kind)

    def move(self, combatant_id: str, cost_ft: int) -> None:
        self.require_turn(combatant_id)
        self.budgets[combatant_id] = self.budgets[combatant_id].move(cost_ft)

    def dash(self, combatant_id: str) -> None:
        self.spend(combatant_id, ActionKind.ACTION)
        budget = self.budgets[combatant_id]
        speed = next(c.speed_ft for c in self.order if c.id == combatant_id)
        self.budgets[combatant_id] = replace(budget, movement_ft=budget.movement_ft + speed, dashed=True)

    def disengage(self, combatant_id: str) -> None:
        self.spend(combatant_id, ActionKind.ACTION)
        self.budgets[combatant_id] = replace(self.budgets[combatant_id], disengaged=True)

    def remove(self, combatant_id: str) -> None:
        self.removed.add(combatant_id)
        if len(self.removed) == len(self.order):
            raise RuleViolation("No quedan combatientes.")
        if self.current.id == combatant_id:
            self.next_turn()

    def next_turn(self) -> Combatant:
        for _ in range(len(self.order)):
            self.index += 1
            if self.index >= len(self.order):
                self.index = 0
                self.round += 1
            if self.current.id not in self.removed:
                break
        current = self.current
        # Al empezar su turno, recupera acción, adicional, reacción y movimiento.
        self.budgets[current.id] = TurnBudget(movement_ft=current.speed_ft)
        return current


def provokes_opportunity_attack(was_in_reach: bool, is_in_reach: bool, disengaged: bool) -> bool:
    """Salir del alcance de un enemigo provoca ataque de oportunidad, salvo con Retirarse."""
    return was_in_reach and not is_in_reach and not disengaged
