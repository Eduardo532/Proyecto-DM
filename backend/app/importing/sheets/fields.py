"""Fichas con campos de formulario: exportación de D&D Beyond y hoja oficial rellenable de WotC."""

from __future__ import annotations

import re

from app.importing.sheets.model import ABILITIES, ParsedSheet, attack_from, parse_class_level, parse_speed
from app.importing.vocab import DAMAGE_TYPES, fold, skill_key, to_int

ABILITY_FIELDS = {"str": "str", "dex": "dex", "con": "con", "int": "int", "wis": "wis", "cha": "cha"}
SAVE_FIELDS = {
    "st strength": "str", "st dexterity": "dex", "st constitution": "con",
    "st intelligence": "int", "st wisdom": "wis", "st charisma": "cha",
}
SAVE_PROF_FIELDS = {"strprof": "str", "dexprof": "dex", "conprof": "con", "intprof": "int", "wisprof": "wis",
                    "chaprof": "cha"}
SHEET_MARKERS = {"charactername", "class level", "classlevel"}
LEVEL_WORDS = {"cantrips": 0, "cantrip": 0, "trucos": 0}


def is_character_form(fields: list[tuple[str, str, int]]) -> bool:
    names = {fold(n) for n, _, _ in fields}
    return bool(names & SHEET_MARKERS) and ("str" in names or "strmod" in names)


def parse_fields(fields: list[tuple[str, str, int]]) -> ParsedSheet:
    values: dict[str, str] = {}
    for name, value, _page in fields:
        key = fold(name)
        if value and key not in values:
            values[key] = value.strip()
    producer = "dndbeyond" if "additionalsenses" in values or "featurestraits1" in values else "wotc_form"
    sheet = ParsedSheet(format=producer)
    sheet.name = values.get("charactername", "")
    classes, subclass, level = parse_class_level(values.get("class level") or values.get("classlevel") or "")
    sheet.char_class, sheet.subclass, sheet.level = classes, subclass, level
    sheet.race = values.get("race") or values.get("species") or ""
    sheet.background = values.get("background", "")
    sheet.alignment = values.get("alignment", "")
    sheet.player_name = values.get("player name") or values.get("playername") or ""
    sheet.xp = to_int(values.get("experience points") or values.get("xp")) or 0

    # Características: según el exportador, el número está en «STR» o en «STRmod».
    for key in ABILITIES:
        first, second = values.get(key, ""), values.get(f"{key}mod") or values.get("chamod" if key == "cha" else "")
        for candidate in (first, second):
            text = (candidate or "").strip()
            if re.fullmatch(r"\d{1,2}", text) and 1 <= int(text) <= 30:
                sheet.abilities[key] = int(text)
                break

    for field_name, ability in SAVE_FIELDS.items():
        bonus = to_int(values.get(field_name))
        if bonus is not None:
            sheet.save_bonus[ability] = bonus
    for field_name, ability in SAVE_PROF_FIELDS.items():
        if values.get(field_name):
            sheet.save_marks.add(ability)

    for name, value, _ in fields:
        key = fold(name)
        skill = skill_key(key.replace(" ", "")) or skill_key(key)
        if skill and value and re.fullmatch(r"[+\-\u2212]?\d{1,2}", value.strip()):
            sheet.skill_bonus.setdefault(skill, to_int(value) or 0)
        if key.endswith("prof") and value:
            skill = skill_key(key[:-4].strip())
            if skill:
                sheet.skill_marks[skill] = value.strip().upper()[:1]

    sheet.proficiency = to_int(values.get("profbonus"))
    sheet.hp_max = to_int(values.get("maxhp") or values.get("hpmax"))
    sheet.hp_current = to_int(values.get("currenthp") or values.get("hpcurrent"))
    sheet.armor_class = to_int(values.get("ac"))
    sheet.speed_ft = parse_speed(values.get("speed", ""))
    hit_dice = values.get("total") or values.get("hdtotal") or values.get("hd") or ""
    die = re.search(r"d(\d+)", hit_dice)
    sheet.hit_die = f"d{die.group(1)}" if die else ""
    senses = values.get("additionalsenses", "") + " " + values.get("senses", "")
    darkvision = re.search(r"darkvision\s*(\d+)", senses, re.IGNORECASE)
    sheet.darkvision_ft = int(darkvision.group(1)) if darkvision else 0
    defenses = fold(values.get("defenses", ""))
    if "resist" in defenses:
        sheet.resistances = [key for word, key in DAMAGE_TYPES.items() if re.search(rf"\b{word}\b", defenses)]

    _attacks(sheet, values)
    _spells(sheet, fields)
    _equipment(sheet, values)
    _texts(sheet, values)
    return sheet


def _attacks(sheet: ParsedSheet, values: dict[str, str]) -> None:
    for index in range(1, 30):
        suffix = "" if index == 1 else f" {index}"
        name = values.get(f"wpn name{suffix}")
        if not name:
            continue
        bonus = to_int(values.get(f"wpn{index} atkbonus"))
        damage = values.get(f"wpn{index} damage", "")
        notes = values.get(f"wpn notes {index}", "")
        sheet.attacks.append(attack_from(name, bonus, damage, sheet, notes))


def _spells(sheet: ParsedSheet, fields: list[tuple[str, str, int]]) -> None:
    level = 0
    seen: set[str] = set()
    for name, value, _ in fields:
        key = fold(name)
        if not value:
            continue
        if key.startswith("spellcastingability") and not sheet.spellcasting_ability:
            ability = fold(value)[:3]
            sheet.spellcasting_ability = ability if ability in ABILITIES else None
        elif key.startswith("spellheader"):
            text = fold(value)
            match = re.search(r"(\d)(?:st|nd|rd|th)? level", text)
            level = int(match.group(1)) if match else LEVEL_WORDS.get(text.split()[0] if text else "", 0)
        elif key.startswith("spellslotheader"):
            slots = re.search(r"(\d+)\s*slots?", value, re.IGNORECASE)
            if slots and level > 0:
                sheet.spell_slots[str(level)] = {"max": int(slots.group(1)), "used": 0}
        elif re.fullmatch(r"spellname\d+", key.replace(" ", "")) and value not in seen:
            seen.add(value)
            sheet.spells.append({"name": value.strip(), "level": level, "prepared": True, "description": ""})


def _equipment(sheet: ParsedSheet, values: dict[str, str]) -> None:
    for index in range(0, 120):
        name = values.get(f"eq name{index}")
        if not name:
            continue
        quantity = to_int(values.get(f"eq qty{index}")) or 1
        weight = re.search(r"[\d.]+", values.get(f"eq weight{index}", ""))
        sheet.inventory.append({"name": name, "quantity": quantity, "equipped": False,
                                "weight_lb": float(weight.group(0)) if weight else 0.0, "notes": ""})
    if not sheet.inventory and values.get("equipment"):
        for line in values["equipment"].splitlines():
            if line.strip():
                sheet.inventory.append({"name": line.strip()[:80], "quantity": 1, "equipped": False,
                                        "weight_lb": 0.0, "notes": ""})
    for coin in ("cp", "sp", "ep", "gp", "pp"):
        amount = to_int(values.get(coin))
        if amount:
            sheet.coins[coin] = amount


def _texts(sheet: ParsedSheet, values: dict[str, str]) -> None:
    profs = values.get("proficiencieslang", "")
    languages = re.search(r"=== ?LANGUAGES ?===\s*(.+?)(?:===|$)", profs, re.DOTALL | re.IGNORECASE)
    if languages:
        sheet.languages = [x.strip() for x in re.split(r"[,\n]", languages.group(1)) if x.strip()]
    sheet.other_proficiencies = [
        x.strip() for x in re.split(r"[,\n]", re.sub(r"=== ?LANGUAGES ?===.*", "", profs, flags=re.DOTALL | re.I))
        if x.strip() and "===" not in x
    ][:40]
    features_text = "\n".join(values.get(f"featurestraits{i}", "") for i in range(1, 10)) or values.get(
        "features and traits", ""
    )
    for match in re.finditer(r"^\*\s*([^•\n|]+?)\s*(?:•|$)", features_text, re.MULTILINE):
        name = match.group(1).strip()
        if name and name.lower() not in {"hit points", "proficiencies"}:
            sheet.features.append({"name": name[:80], "description": "", "uses_max": None, "uses_used": 0})
    parts = [values.get(k, "") for k in ("personalitytraits", "ideals", "bonds", "flaws")]
    labels = ("Rasgos", "Ideales", "Vínculos", "Defectos")
    sheet.personality = "\n".join(f"{label}: {text}" for label, text in zip(labels, parts, strict=True) if text)
