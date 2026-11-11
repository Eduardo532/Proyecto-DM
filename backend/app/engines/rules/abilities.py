"""Características, habilidades, competencia y dificultades (SRD 5.1)."""

from enum import StrEnum


class Ability(StrEnum):
    STR = "str"
    DEX = "dex"
    CON = "con"
    INT = "int"
    WIS = "wis"
    CHA = "cha"


ABILITY_LABELS: dict[Ability, tuple[str, str]] = {
    Ability.STR: ("Fuerza", "FUE"),
    Ability.DEX: ("Destreza", "DES"),
    Ability.CON: ("Constitución", "CON"),
    Ability.INT: ("Inteligencia", "INT"),
    Ability.WIS: ("Sabiduría", "SAB"),
    Ability.CHA: ("Carisma", "CAR"),
}

# Habilidad -> (característica, nombre en español)
SKILLS: dict[str, tuple[Ability, str]] = {
    "acrobatics": (Ability.DEX, "Acrobacias"),
    "animal_handling": (Ability.WIS, "Trato con Animales"),
    "arcana": (Ability.INT, "Conocimiento Arcano"),
    "athletics": (Ability.STR, "Atletismo"),
    "deception": (Ability.CHA, "Engaño"),
    "history": (Ability.INT, "Historia"),
    "insight": (Ability.WIS, "Perspicacia"),
    "intimidation": (Ability.CHA, "Intimidación"),
    "investigation": (Ability.INT, "Investigación"),
    "medicine": (Ability.WIS, "Medicina"),
    "nature": (Ability.INT, "Naturaleza"),
    "perception": (Ability.WIS, "Percepción"),
    "performance": (Ability.CHA, "Interpretación"),
    "persuasion": (Ability.CHA, "Persuasión"),
    "religion": (Ability.INT, "Religión"),
    "sleight_of_hand": (Ability.DEX, "Juego de Manos"),
    "stealth": (Ability.DEX, "Sigilo"),
    "survival": (Ability.WIS, "Supervivencia"),
}

# Dificultades estándar del SRD. La IA elige la categoría; el número lo pone el motor.
DIFFICULTY_CLASSES: dict[str, int] = {
    "muy_facil": 5,
    "facil": 10,
    "media": 15,
    "dificil": 20,
    "muy_dificil": 25,
    "casi_imposible": 30,
}

# Experiencia necesaria para cada nivel (PHB 2014 / SRD 5.1).
XP_THRESHOLDS: tuple[int, ...] = (
    0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000,
    85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000,
)  # fmt: skip


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def proficiency_bonus(level: int) -> int:
    if not 1 <= level <= 20:
        raise ValueError("El nivel debe estar entre 1 y 20.")
    return 2 + (level - 1) // 4


def level_for_xp(xp: int) -> int:
    level = 1
    for index, threshold in enumerate(XP_THRESHOLDS):
        if xp >= threshold:
            level = index + 1
    return level


def skill_label(skill: str) -> str:
    return SKILLS[skill][1]
