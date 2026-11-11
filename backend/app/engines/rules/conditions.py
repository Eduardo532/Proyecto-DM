"""Condiciones de 5e (2014) y su efecto en las tiradas."""

from enum import StrEnum

from app.engines.rules.dice import Advantage


class Condition(StrEnum):
    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"


CONDITION_LABELS: dict[Condition, str] = {
    Condition.BLINDED: "Cegado",
    Condition.CHARMED: "Hechizado",
    Condition.DEAFENED: "Ensordecido",
    Condition.FRIGHTENED: "Asustado",
    Condition.GRAPPLED: "Agarrado",
    Condition.INCAPACITATED: "Incapacitado",
    Condition.INVISIBLE: "Invisible",
    Condition.PARALYZED: "Paralizado",
    Condition.PETRIFIED: "Petrificado",
    Condition.POISONED: "Envenenado",
    Condition.PRONE: "Derribado",
    Condition.RESTRAINED: "Apresado",
    Condition.STUNNED: "Aturdido",
    Condition.UNCONSCIOUS: "Inconsciente",
}

# Condiciones que impiden actuar (acciones y reacciones).
INCAPACITATING: frozenset[Condition] = frozenset(
    {
        Condition.INCAPACITATED,
        Condition.PARALYZED,
        Condition.PETRIFIED,
        Condition.STUNNED,
        Condition.UNCONSCIOUS,
    }
)

# Condiciones con velocidad 0.
SPEED_ZERO: frozenset[Condition] = frozenset(
    {
        Condition.GRAPPLED,
        Condition.RESTRAINED,
        Condition.PARALYZED,
        Condition.PETRIFIED,
        Condition.STUNNED,
        Condition.UNCONSCIOUS,
    }
)


def roll_modifiers_from_conditions(
    conditions: set[Condition], exhaustion: int, kind: str, ability: str | None = None
) -> list[Advantage]:
    """Ventajas/desventajas que el propio actor sufre por sus condiciones.

    ``kind``: ``ability``, ``skill``, ``save``, ``attack`` o ``initiative``.
    """
    sources: list[Advantage] = []
    is_check = kind in {"ability", "skill", "initiative"}
    if kind == "attack":
        if conditions & {Condition.BLINDED, Condition.FRIGHTENED, Condition.POISONED,
                         Condition.PRONE, Condition.RESTRAINED}:  # fmt: skip
            sources.append(Advantage.DISADVANTAGE)
        if Condition.INVISIBLE in conditions:
            sources.append(Advantage.ADVANTAGE)
    if is_check and conditions & {Condition.FRIGHTENED, Condition.POISONED}:
        sources.append(Advantage.DISADVANTAGE)
    if kind == "save" and ability == "dex" and Condition.RESTRAINED in conditions:
        sources.append(Advantage.DISADVANTAGE)
    if exhaustion >= 1 and is_check:
        sources.append(Advantage.DISADVANTAGE)
    if exhaustion >= 3 and kind in {"attack", "save"}:
        sources.append(Advantage.DISADVANTAGE)
    return sources


def auto_fail_save(conditions: set[Condition], ability: str) -> bool:
    """Paralizado, petrificado, aturdido e inconsciente fallan salvaciones de FUE y DES."""
    blocking = {Condition.PARALYZED, Condition.PETRIFIED, Condition.STUNNED, Condition.UNCONSCIOUS}
    return ability in {"str", "dex"} and bool(conditions & blocking)
