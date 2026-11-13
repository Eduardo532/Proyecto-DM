"""Vocabulario de D&D en español e inglés para reconocer fichas y documentos de distintas fuentes."""

from __future__ import annotations

import re
import unicodedata

from app.engines.rules.abilities import SKILLS


def fold(text: str) -> str:
    """Minúsculas, sin tildes y sin signos: para comparar etiquetas de fuentes distintas."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


ABILITY_NAMES: dict[str, str] = {
    "fuerza": "str", "fue": "str", "strength": "str", "str": "str",
    "destreza": "dex", "des": "dex", "dexterity": "dex", "dex": "dex",
    "constitucion": "con", "con": "con", "constitution": "con",
    "inteligencia": "int", "int": "int", "intelligence": "int",
    "sabiduria": "wis", "sab": "wis", "wisdom": "wis", "wis": "wis",
    "carisma": "cha", "car": "cha", "charisma": "cha", "cha": "cha",
}

SKILL_NAMES: dict[str, str] = {}
for _key, (_ability, _label) in SKILLS.items():
    SKILL_NAMES[fold(_label)] = _key
    SKILL_NAMES[fold(_key.replace("_", " "))] = _key
SKILL_NAMES.update(
    {
        "arcanos": "arcana",
        "c arcano": "arcana",
        "conocimiento arcano": "arcana",
        "engañar": "deception",
        "enganar": "deception",
        "intimidar": "intimidation",
        "trato con los animales": "animal_handling",
        "animal": "animal_handling",
        "juego de manos": "sleight_of_hand",
        "sleightofhand": "sleight_of_hand",
        "sleight of hand": "sleight_of_hand",
        "perspicacia": "insight",
        "interpretacion": "performance",
    }
)

DAMAGE_TYPES: dict[str, str] = {
    "slashing": "slashing", "cortante": "slashing",
    "piercing": "piercing", "perforante": "piercing",
    "bludgeoning": "bludgeoning", "contundente": "bludgeoning",
    "fire": "fire", "fuego": "fire",
    "cold": "cold", "frio": "cold",
    "lightning": "lightning", "relampago": "lightning", "rayo": "lightning",
    "thunder": "thunder", "trueno": "thunder",
    "acid": "acid", "acido": "acid",
    "poison": "poison", "veneno": "poison",
    "necrotic": "necrotic", "necrotico": "necrotic",
    "radiant": "radiant", "radiante": "radiant",
    "force": "force", "fuerza": "force",
    "psychic": "psychic", "psiquico": "psychic",
}

# Nombres de condiciones (incluidos los marcadores de estado de mesas virtuales) -> condición del motor.
CONDITION_NAMES: dict[str, str] = {
    "blinded": "blinded", "blind": "blinded", "cegado": "blinded",
    "charmed": "charmed", "hechizado": "charmed", "encantado": "charmed",
    "deafened": "deafened", "deaf": "deafened", "ensordecido": "deafened",
    "frightened": "frightened", "feared": "frightened", "fear": "frightened", "asustado": "frightened",
    "grappled": "grappled", "agarrado": "grappled",
    "incapacitated": "incapacitated", "incapacitado": "incapacitated",
    "invisible": "invisible",
    "paralyzed": "paralyzed", "paralysed": "paralyzed", "paralizado": "paralyzed",
    "petrified": "petrified", "petrificado": "petrified",
    "poisoned": "poisoned", "envenenado": "poisoned",
    "prone": "prone", "derribado": "prone", "tumbado": "prone",
    "restrained": "restrained", "apresado": "restrained", "inmovilizado": "restrained",
    "stunned": "stunned", "aturdido": "stunned",
    "unconscious": "unconscious", "sleeping": "unconscious", "asleep": "unconscious", "inconsciente": "unconscious",
    "exhausted": "exhaustion", "exhaustion": "exhaustion", "agotado": "exhaustion",
    "concentrating": "concentration", "concentration": "concentration", "concentrado": "concentration",
}


def skill_key(label: str) -> str | None:
    return SKILL_NAMES.get(fold(label))


def ability_key(label: str) -> str | None:
    return ABILITY_NAMES.get(fold(label))


SIGNED = re.compile(r"^[+\-\u2212\u2013]?\d{1,2}$")


def to_int(text: str | None) -> int | None:
    if text is None:
        return None
    match = re.search(r"[+\-\u2212\u2013]?\s*\d+", text)
    if not match:
        return None
    return int(match.group(0).replace(" ", "").replace("\u2212", "-").replace("\u2013", "-"))
