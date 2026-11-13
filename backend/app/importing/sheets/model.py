"""Resultado común de todos los lectores de fichas."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.engines.rules.abilities import SKILLS, ability_modifier, proficiency_bonus
from app.importing.vocab import DAMAGE_TYPES, fold, to_int

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")


@dataclass
class ParsedSheet:
    format: str
    name: str = ""
    player_name: str = ""
    race: str = ""
    char_class: str = ""
    subclass: str = ""
    level: int = 1
    background: str = ""
    alignment: str = ""
    xp: int = 0
    abilities: dict[str, int] = field(default_factory=dict)
    skill_bonus: dict[str, int] = field(default_factory=dict)
    save_bonus: dict[str, int] = field(default_factory=dict)
    skill_marks: dict[str, str] = field(default_factory=dict)  # "P" competencia, "E" pericia, "H" mitad
    save_marks: set[str] = field(default_factory=set)
    proficiency: int | None = None
    hp_max: int | None = None
    hp_current: int | None = None
    armor_class: int | None = None
    speed_ft: int | None = None
    hit_die: str = ""
    darkvision_ft: int = 0
    resistances: list[str] = field(default_factory=list)
    attacks: list[dict[str, Any]] = field(default_factory=list)
    spellcasting_ability: str | None = None
    spells: list[dict[str, Any]] = field(default_factory=list)
    spell_slots: dict[str, dict[str, int]] = field(default_factory=dict)
    features: list[dict[str, Any]] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)
    coins: dict[str, int] = field(default_factory=dict)
    languages: list[str] = field(default_factory=list)
    other_proficiencies: list[str] = field(default_factory=list)
    personality: str = ""
    notes: str = ""
    warnings: list[str] = field(default_factory=list)

    # ---------------------------------------------------------------- resultado ---
    def confidence(self) -> float:
        """Proporción de datos esenciales encontrados (0-1)."""
        checks = [
            bool(self.name),
            bool(self.char_class),
            len(self.abilities) == 6,
            self.hp_max is not None,
            self.armor_class is not None,
            len(self.skill_bonus) >= 12,
        ]
        return round(sum(checks) / len(checks), 2)

    def _prof(self) -> int:
        if self.proficiency:
            return self.proficiency
        return proficiency_bonus(max(1, min(20, self.level)))

    def derive_proficiencies(self) -> tuple[list[str], list[str], list[str], bool]:
        """Competencias a partir de las marcas o, si no hay, de la diferencia bonificador - modificador."""
        prof = self._prof()
        skills: list[str] = []
        expertise: list[str] = []
        jack = False
        for skill, (ability, _) in SKILLS.items():
            mark = self.skill_marks.get(skill, "")
            if mark:
                if mark == "E":
                    expertise.append(skill)
                    skills.append(skill)
                elif mark == "P":
                    skills.append(skill)
                elif mark == "H":
                    jack = True
                continue
            bonus = self.skill_bonus.get(skill)
            score = self.abilities.get(ability.value)
            if bonus is None or score is None:
                continue
            extra = bonus - ability_modifier(score)
            if extra >= 2 * prof:
                expertise.append(skill)
                skills.append(skill)
            elif extra >= prof:
                skills.append(skill)
            elif extra == prof // 2 and prof // 2 > 0:
                jack = True
        saves = sorted(self.save_marks)
        if not saves:
            for key in ABILITIES:
                bonus = self.save_bonus.get(key)
                score = self.abilities.get(key)
                if bonus is not None and score is not None and bonus - ability_modifier(score) >= prof:
                    saves.append(key)
        return skills, expertise, saves, jack

    def to_character(self) -> dict[str, Any]:
        """Datos listos para ``CharacterCreate`` (el usuario los revisa antes de confirmar)."""
        skills, expertise, saves, jack = self.derive_proficiencies()
        abilities = {a: int(self.abilities.get(a, 10)) for a in ABILITIES}
        con_mod = ability_modifier(abilities["con"])
        hp_max = self.hp_max or max(1, 8 + con_mod + (self.level - 1) * (5 + con_mod))
        if self.hp_max is None:
            self.warnings.append("No se encontraron los PG máximos: se ha puesto una estimación.")
        if len(self.abilities) < 6:
            self.warnings.append("Faltan características: revisa los valores (10 por defecto).")
        if self.spells and not self.spell_slots:
            self.spell_slots = estimate_slots(self.char_class, self.level)
            if self.spell_slots:
                self.warnings.append("Espacios de conjuro estimados según clase y nivel: revísalos.")
        self.warnings = list(dict.fromkeys(self.warnings))
        return {
            "name": self.name or "Personaje importado",
            "race": self.race,
            "char_class": self.char_class,
            "subclass": self.subclass,
            "level": max(1, min(20, self.level)),
            "background": self.background,
            "alignment": self.alignment,
            "xp": max(0, self.xp),
            "hp_max": hp_max,
            "hp_current": min(self.hp_current or hp_max, hp_max),
            "armor_class": self.armor_class or 10 + ability_modifier(abilities["dex"]),
            "speed_ft": self.speed_ft or 30,
            "notes": self.notes,
            "sheet": {
                "abilities": abilities,
                "skill_proficiencies": skills,
                "skill_expertise": expertise,
                "save_proficiencies": saves,
                "jack_of_all_trades": jack,
                "darkvision_ft": self.darkvision_ft,
                "resistances": sorted(set(self.resistances)),
                "attacks": self.attacks,
                "spellcasting_ability": self.spellcasting_ability,
                "spells": self.spells,
                "spell_slots": self.spell_slots,
                "features": self.features,
                "inventory": self.inventory,
                "coins": {k: self.coins.get(k, 0) for k in ("cp", "sp", "ep", "gp", "pp")},
                "languages": self.languages,
                "other_proficiencies": self.other_proficiencies,
                "hit_die": self.hit_die or "d8",
                "personality": self.personality,
            },
        }


# ------------------------------------------------------------------ utilidades ---
FULL_CASTER_SLOTS = [
    [2], [3], [4, 2], [4, 3], [4, 3, 2], [4, 3, 3], [4, 3, 3, 1], [4, 3, 3, 2], [4, 3, 3, 3, 1],
    [4, 3, 3, 3, 2], [4, 3, 3, 3, 2, 1], [4, 3, 3, 3, 2, 1], [4, 3, 3, 3, 2, 1, 1], [4, 3, 3, 3, 2, 1, 1],
    [4, 3, 3, 3, 2, 1, 1, 1], [4, 3, 3, 3, 2, 1, 1, 1], [4, 3, 3, 3, 2, 1, 1, 1, 1], [4, 3, 3, 3, 3, 1, 1, 1, 1],
    [4, 3, 3, 3, 3, 2, 1, 1, 1], [4, 3, 3, 3, 3, 2, 2, 1, 1],
]
FULL_CASTERS = {"bardo", "bard", "clerigo", "cleric", "druida", "druid", "hechicero", "sorcerer", "mago", "wizard"}
HALF_CASTERS = {"paladin", "explorador", "ranger"}


def estimate_slots(char_class: str, level: int) -> dict[str, dict[str, int]]:
    """Espacios de conjuro de una clase simple (lanzador completo o medio); vacío si no aplica."""
    key = fold(char_class.split("/")[0]).split(" ")[0] if char_class else ""
    level = max(1, min(20, level))
    if key in FULL_CASTERS:
        slots = FULL_CASTER_SLOTS[level - 1]
    elif key in HALF_CASTERS and level >= 2:
        slots = FULL_CASTER_SLOTS[(level + 1) // 2 - 1]
    else:
        return {}
    return {str(i + 1): {"max": n, "used": 0} for i, n in enumerate(slots)}


CLASS_LEVEL = re.compile(r"([A-Za-zÁÉÍÓÚÑáéíóúñü' ]+?)\s+(\d{1,2})(?:\s*\(([^)]+)\))?")


def parse_class_level(text: str) -> tuple[str, str, int]:
    """«Fighter 3», «Paladín 3 / Brujo 2», «Cleric 3 (Life Domain)» → (clases, subclase, nivel total)."""
    parts = CLASS_LEVEL.findall(text)
    if not parts:
        return text.strip(), "", 1
    classes = " / ".join(p[0].strip().title() if p[0].isupper() else p[0].strip() for p in parts)
    subclass = next((p[2].strip() for p in parts if p[2]), "")
    return classes, subclass, sum(int(p[1]) for p in parts)


def parse_speed(text: str) -> int | None:
    value = to_int(text)
    if value is None:
        return None
    if re.search(r"\bm\b|metros", text) and value < 20:
        return round(value / 1.5) * 5  # 9 m -> 30 pies
    return value


def parse_damage(text: str) -> tuple[str, str]:
    """«1d8+3 Slashing» o «2d6 +2 de daño contundente» → («1d8», «slashing»)."""
    dice = re.search(r"\d+d\d+", text.replace("D", "d"))
    damage_type = "bludgeoning"
    tokens = fold(text).split()
    for word, key in DAMAGE_TYPES.items():
        if key == "force" and word == "fuerza":
            continue
        if any(t == word or (len(t) >= 5 and word.startswith(t)) for t in tokens):
            damage_type = key
            break
    return (dice.group(0) if dice else "1"), damage_type


def attack_from(name: str, bonus: int | None, damage_text: str, sheet: ParsedSheet, notes: str = "") -> dict[str, Any]:
    """Construye un ataque e infiere la característica comparando el bonificador con FUE y DES."""
    dice, damage_type = parse_damage(damage_text)
    prof = sheet._prof()
    best = "str"
    extra = 0
    if bonus is not None:
        candidates = []
        for order, ability in enumerate(("str", "dex", "cha", "wis", "int")):
            score = sheet.abilities.get(ability)
            if score is not None:
                candidates.append((abs(bonus - (ability_modifier(score) + prof)), order, ability))
        if candidates:
            best = min(candidates)[2]
            extra = bonus - (ability_modifier(sheet.abilities[best]) + prof)
    finesse = "finesse" in notes.lower() or "sutil" in notes.lower()
    ranged = re.search(r"range|alcance|\(\d+/\d+\)", notes.lower()) is not None
    return {
        "name": name.strip()[:80],
        "ability": "dex" if finesse and best == "str" else best,
        "proficient": True,
        "attack_bonus_extra": max(-5, min(5, extra)),
        "damage": dice,
        "damage_type": damage_type,
        "reach_ft": 5,
        "range_ft": 80 if ranged else None,
        "range_long_ft": None,
    }
