"""Dados: expresiones, tiradas digitales y manuales, ventaja y desventaja."""

from __future__ import annotations

import random
import re
import secrets
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, Protocol

from app.engines.errors import RuleViolation

DIE_SIZES: tuple[int, ...] = (4, 6, 8, 10, 12, 20, 100)
MAX_DICE_PER_TERM = 100


class RandomSource(Protocol):
    def randint(self, a: int, b: int) -> int: ...


def system_random() -> RandomSource:
    """Generador criptográficamente seguro para tiradas reales."""
    return secrets.SystemRandom()


def seeded_random(seed: int) -> RandomSource:
    """Generador reproducible para pruebas."""
    return random.Random(seed)


class Advantage(StrEnum):
    NONE = "none"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"


def combine_advantage(sources: list[Advantage]) -> Advantage:
    """Regla 2014: si hay al menos una fuente de cada, se anulan; no se acumulan."""
    has_adv = Advantage.ADVANTAGE in sources
    has_dis = Advantage.DISADVANTAGE in sources
    if has_adv and not has_dis:
        return Advantage.ADVANTAGE
    if has_dis and not has_adv:
        return Advantage.DISADVANTAGE
    return Advantage.NONE


KeepMode = Literal["all", "highest", "lowest"]


@dataclass(frozen=True)
class DieTerm:
    count: int
    sides: int
    sign: int = 1
    keep: KeepMode = "all"
    keep_count: int = 0

    def __str__(self) -> str:
        suffix = ""
        if self.keep == "highest":
            suffix = f"kh{self.keep_count}"
        elif self.keep == "lowest":
            suffix = f"kl{self.keep_count}"
        return f"{self.count}d{self.sides}{suffix}"


@dataclass(frozen=True)
class DiceExpression:
    terms: tuple[DieTerm, ...]
    modifier: int = 0

    @property
    def dice_count(self) -> int:
        return sum(t.count for t in self.terms)

    def __str__(self) -> str:
        parts: list[str] = []
        for term in self.terms:
            sign = "-" if term.sign < 0 else "+"
            parts.append(f"{sign}{term}")
        if self.modifier:
            parts.append(f"{'+' if self.modifier > 0 else '-'}{abs(self.modifier)}")
        text = "".join(parts)
        return text[1:] if text.startswith("+") else text or "0"


_TOKEN = re.compile(r"([+-]?)\s*(?:(\d*)d(\d+)(?:(kh|kl)(\d+))?|(\d+))", re.IGNORECASE)


def parse(expression: str) -> DiceExpression:
    """Convierte ``"2d6+3"``, ``"4d6kh3"`` o ``"1d8+2d6-1"`` en una expresión."""
    text = expression.replace(" ", "").lower()
    if not text:
        raise RuleViolation("La expresión de dados está vacía.")
    pos = 0
    terms: list[DieTerm] = []
    modifier = 0
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if not match or match.end() == pos:
            raise RuleViolation(f"Expresión de dados no válida: \"{expression}\".")
        if pos > 0 and not match.group(1):
            raise RuleViolation(f"Falta un signo + o - en \"{expression}\".")
        sign = -1 if match.group(1) == "-" else 1
        if match.group(6) is not None:
            modifier += sign * int(match.group(6))
        else:
            count = int(match.group(2) or 1)
            sides = int(match.group(3))
            if sides not in DIE_SIZES:
                raise RuleViolation(f"Dado no admitido: d{sides}.")
            if not 1 <= count <= MAX_DICE_PER_TERM:
                raise RuleViolation(f"Cantidad de dados no válida: {count}.")
            keep: KeepMode = "all"
            keep_count = 0
            if match.group(4):
                keep = "highest" if match.group(4) == "kh" else "lowest"
                keep_count = int(match.group(5))
                if not 1 <= keep_count <= count:
                    raise RuleViolation("No se pueden conservar más dados de los tirados.")
            terms.append(DieTerm(count, sides, sign, keep, keep_count))
        pos = match.end()
    return DiceExpression(tuple(terms), modifier)


@dataclass(frozen=True)
class TermResult:
    term: DieTerm
    rolls: tuple[int, ...]
    kept: tuple[int, ...]

    @property
    def subtotal(self) -> int:
        return self.term.sign * sum(self.kept)


@dataclass(frozen=True)
class RollResult:
    expression: DiceExpression
    terms: tuple[TermResult, ...]
    mode: Literal["digital", "manual"]

    @property
    def total(self) -> int:
        return sum(t.subtotal for t in self.terms) + self.expression.modifier

    def describe(self) -> str:
        parts = [f"{t.term}{list(t.rolls)}" for t in self.terms]
        if self.expression.modifier:
            parts.append(str(self.expression.modifier))
        return " + ".join(parts) + f" = {self.total}"


def _keep(term: DieTerm, rolls: list[int]) -> tuple[int, ...]:
    if term.keep == "all":
        return tuple(rolls)
    ordered = sorted(rolls, reverse=term.keep == "highest")
    return tuple(ordered[: term.keep_count])


def roll(expression: DiceExpression | str, rng: RandomSource | None = None) -> RollResult:
    expr = parse(expression) if isinstance(expression, str) else expression
    source = rng or system_random()
    results = []
    for term in expr.terms:
        rolls = [source.randint(1, term.sides) for _ in range(term.count)]
        results.append(TermResult(term, tuple(rolls), _keep(term, rolls)))
    return RollResult(expr, tuple(results), "digital")


def roll_manual(expression: DiceExpression | str, values: list[int]) -> RollResult:
    """Registra dados físicos. Valida que haya un valor por dado y que esté en rango."""
    expr = parse(expression) if isinstance(expression, str) else expression
    if len(values) != expr.dice_count:
        raise RuleViolation(f"Se esperaban {expr.dice_count} valores de dado y llegaron {len(values)}.")
    results = []
    index = 0
    for term in expr.terms:
        rolls = values[index : index + term.count]
        index += term.count
        for value in rolls:
            if not 1 <= value <= term.sides:
                raise RuleViolation(f"El valor {value} no es posible en un d{term.sides}.")
        results.append(TermResult(term, tuple(rolls), _keep(term, rolls)))
    return RollResult(expr, tuple(results), "manual")


@dataclass(frozen=True)
class D20Roll:
    """Una tirada de d20 con ventaja o desventaja ya aplicada."""

    rolls: tuple[int, ...]
    advantage: Advantage
    mode: Literal["digital", "manual"] = "digital"
    natural: int = field(init=False)

    def __post_init__(self) -> None:
        expected = 1 if self.advantage is Advantage.NONE else 2
        if len(self.rolls) != expected:
            raise RuleViolation(f"Se esperaban {expected} dados d20 y llegaron {len(self.rolls)}.")
        for value in self.rolls:
            if not 1 <= value <= 20:
                raise RuleViolation(f"El valor {value} no es posible en un d20.")
        if self.advantage is Advantage.ADVANTAGE:
            natural = max(self.rolls)
        elif self.advantage is Advantage.DISADVANTAGE:
            natural = min(self.rolls)
        else:
            natural = self.rolls[0]
        object.__setattr__(self, "natural", natural)


def roll_d20(advantage: Advantage = Advantage.NONE, rng: RandomSource | None = None) -> D20Roll:
    source = rng or system_random()
    count = 1 if advantage is Advantage.NONE else 2
    return D20Roll(tuple(source.randint(1, 20) for _ in range(count)), advantage)


def critical_damage(expression: DiceExpression) -> DiceExpression:
    """Crítico (2014): se duplican los dados de daño, no el modificador."""
    terms = tuple(
        DieTerm(t.count * 2, t.sides, t.sign, t.keep, t.keep_count * 2 if t.keep != "all" else 0)
        for t in expression.terms
    )
    return DiceExpression(terms, expression.modifier)
