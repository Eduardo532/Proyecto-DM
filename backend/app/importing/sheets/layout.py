"""Fichas sin campos de formulario (Nivel20, hojas impresas, exportaciones a PDF «planas»).

Se leen por posición: cada dato está junto a su etiqueta (a la derecha, debajo o encima, según la
hoja). Las competencias se deducen comparando el bonificador con el modificador de la característica.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Iterable

from app.engines.rules.abilities import ability_modifier
from app.importing.pdftext import Word, lines
from app.importing.sheets.model import ParsedSheet, attack_from, parse_class_level, parse_speed
from app.importing.vocab import ABILITY_NAMES, DAMAGE_TYPES, SKILL_NAMES, fold, to_int

CLASSES = {
    "barbaro", "bardo", "brujo", "clerigo", "druida", "explorador", "guerrero", "hechicero", "mago", "monje",
    "paladin", "picaro", "artifice", "barbarian", "bard", "warlock", "cleric", "druid", "ranger", "fighter",
    "sorcerer", "wizard", "monk", "rogue", "artificer",
}
HEADER_LABELS: dict[str, list[str]] = {
    "name": ["nombre del personaje", "character name"],
    "class": ["clase y nivel", "class level", "class and level"],
    "race": ["raza", "especie", "race", "species"],
    "background": ["trasfondo", "background"],
    "alignment": ["alineamiento", "alignment"],
    "player": ["jugador", "player name"],
    "xp": ["puntos de experiencia", "experiencia", "experience points"],
    "languages": ["idiomas", "languages"],
    "speed": ["velocidad", "speed"],
}
ALL_LABELS = sorted({lab for labs in HEADER_LABELS.values() for lab in labs} | {
    "tamano", "size", "percepcion pasiva", "passive perception", "inspiracion", "inspiration", "competencia",
    "iniciativa", "initiative", "proficiency bonus",
}, key=len, reverse=True)
SIGNED_RE = re.compile(r"^[+\-\u2212\u2013]\d{1,2}$|^0$")
UNSIGNED_RE = re.compile(r"^\d{1,2}$")
PRIVATE_USE = re.compile(r"[-]")


def _norm_words(row: list[Word]) -> list[str]:
    return [fold(w.text) for w in row]


def _find_phrase(row: list[Word], phrase: str) -> tuple[int, int] | None:
    target = phrase.split()
    folded = _norm_words(row)
    for i in range(len(folded) - len(target) + 1):
        if folded[i : i + len(target)] == target:
            return i, i + len(target)
    return None


def _label_starts(row: list[Word]) -> list[int]:
    starts = []
    for label in ALL_LABELS:
        found = _find_phrase(row, label)
        if found:
            starts.append(found[0])
    return sorted(set(starts))


def column_starts(rows: list[list[Word]], widths: list[float]) -> dict[int, set[int]]:
    """Posiciones x donde empiezan columnas de texto: muchos renglones arrancan justo ahí tras un hueco."""
    counts: dict[tuple[int, int], int] = {}
    for row in rows:
        width = widths[row[0].page] if row[0].page < len(widths) else 600.0
        candidates = [row[0]] + [w for prev, w in itertools.pairwise(row) if w.x0 - prev.x1 >= 6]
        for word in candidates:
            if word.x0 > width * 0.3:
                key = (word.page, round(word.x0 / 3))
                counts[key] = counts.get(key, 0) + 1
    starts: dict[int, set[int]] = {}
    for (page, bucket), count in sorted(counts.items()):
        if count >= 6:
            page_starts = starts.setdefault(page, set())
            if not any(abs(bucket - s) <= 2 for s in page_starts):  # agrupa posiciones casi iguales
                page_starts.add(bucket)
    return starts


def split_columns(rows: list[list[Word]], widths: list[float]) -> list[list[Word]]:
    """Separa los renglones que atraviesan varias columnas de texto."""
    starts = column_starts(rows, widths)
    result: list[list[Word]] = []
    for row in rows:
        page_starts = starts.get(row[0].page, set())
        current: list[Word] = []
        for index, word in enumerate(row):
            gap = word.x0 - row[index - 1].x1 if index else 0
            at_start = gap >= 6 and any(-1 <= round(word.x0 / 3) - s <= 3 for s in page_starts)
            if current and (at_start or gap >= 45):
                result.append(current)
                current = []
            current.append(word)
        if current:
            result.append(current)
    return result


class Layout:
    def __init__(self, words: list[Word], widths: list[float] | None = None) -> None:
        self.words = [w for w in words if not PRIVATE_USE.fullmatch(w.text)]
        self.glyphs = [w for w in words if PRIVATE_USE.search(w.text)]
        self.widths = widths or [600.0]
        self.raw_rows = lines(self.words)
        self.rows = split_columns(self.raw_rows, self.widths)
        self.starts = column_starts(lines(self.words), self.widths)

    def column(self, word: Word) -> int:
        return sum(1 for s in self.starts.get(word.page, set()) if s * 3 <= word.x0 + 4)

    def near(self, anchor: Word, *, right: float = 0, below: float = 0, above: float = 0, width: float = 60,
             pattern: re.Pattern[str] = SIGNED_RE, exclude: set[int] | None = None) -> Word | None:
        """Palabra que cumple ``pattern`` más cercana al ancla en la dirección pedida."""
        found = self.near_all(anchor, right=right, below=below, above=above, width=width, pattern=pattern,
                              exclude=exclude)
        return found[0] if found else None

    def near_all(self, anchor: Word, *, right: float = 0, below: float = 0, above: float = 0, width: float = 60,
                 pattern: re.Pattern[str] = SIGNED_RE, exclude: set[int] | None = None) -> list[Word]:
        """Todas las palabras candidatas, de la más cercana a la más lejana."""
        scored: list[tuple[float, Word]] = []
        for word in self.words:
            if word.page != anchor.page or word is anchor or not pattern.match(word.text.replace("\u2212", "-")):
                continue
            if exclude and id(word) in exclude:
                continue
            dx, dy = word.x0 - anchor.x1, word.cy - anchor.cy
            if right and abs(dy) <= 4 and -2 <= dx <= right:
                score = dx
            elif below and 2 < dy <= below and abs(word.cx - anchor.cx) <= width:
                score = 100 + dy + abs(word.cx - anchor.cx) / 4
            elif above and -above <= dy < -2 and abs(word.cx - anchor.cx) <= width:
                score = 200 - dy + abs(word.cx - anchor.cx) / 4
            else:
                continue
            scored.append((score, word))
        scored.sort(key=lambda item: item[0])
        return [word for _, word in scored]

    def label_value(self, labels: Iterable[str]) -> str:
        """Texto del dato asociado a una etiqueta: a su derecha, debajo («Idiomas:») o encima (hoja oficial)."""
        labels = list(labels)
        for row_index, row in enumerate(self.rows):
            for label in labels:
                found = _find_phrase(row, label)
                if not found or not row[found[1] - 1].text.endswith(":"):
                    continue
                right = " ".join(w.text for w in row[found[1] :]).strip()
                if right:
                    return right
                for nxt in self.rows[row_index + 1 : row_index + 4]:
                    below = -4 < nxt[0].y0 - row[0].y1 < 16 and abs(nxt[0].x0 - row[0].x0) < 20
                    if nxt[0].page == row[0].page and below:
                        return " ".join(w.text for w in nxt)
        for row_index, row in enumerate(self.rows):
            for label in labels:
                found = _find_phrase(row, label)
                if not found:
                    continue
                start, end = found
                following = [s for s in _label_starts(row) if s >= end]
                stop = following[0] if following else len(row)
                right = " ".join(w.text for w in row[end:stop]).strip()
                if right and fold(right) not in ALL_LABELS:
                    return right
                anchor = row[start]
                for prev in reversed(self.rows[max(0, row_index - 3) : row_index]):
                    if prev[0].page != anchor.page or anchor.y0 - prev[0].y1 > 22:
                        continue
                    chunk = [w for w in prev if anchor.x0 - 8 <= w.x0 <= anchor.x0 + 120]
                    if chunk:
                        return " ".join(w.text for w in chunk)
        return ""

    def phrase_anchor(self, phrases: Iterable[str]) -> Word | None:
        for row in self.rows:
            for phrase in phrases:
                found = _find_phrase(row, phrase)
                if found:
                    return row[found[0]]
        return None

    def text_lines(self) -> list[str]:
        """Renglones en orden de lectura: página, columna y altura."""
        ordered = sorted(self.rows, key=lambda r: (r[0].page, self.column(r[0]), r[0].cy, r[0].x0))
        return [" ".join(w.text for w in row) for row in ordered]


def parse_layout(words: list[Word], widths: list[float] | None = None, fmt: str = "texto") -> ParsedSheet:
    layout = Layout(words, widths)
    first_page = [w for w in layout.words if w.page == 0]
    sheet = ParsedSheet(format=fmt)
    _header(layout, sheet, first_page)
    _abilities(layout, sheet)
    _skills_and_saves(layout, sheet)
    _combat(layout, sheet)
    _attacks(layout, sheet)
    _spells(layout, sheet)
    _features(layout, sheet)
    return sheet


# --------------------------------------------------------------------- cabecera ---
def _header(layout: Layout, sheet: ParsedSheet, first_page: list[Word]) -> None:
    sheet.name = layout.label_value(HEADER_LABELS["name"])
    class_text = layout.label_value(HEADER_LABELS["class"])
    if not class_text or not sheet.name:
        # Formato compacto: «ARMANDO LIOS  PALADÍN 3» en el primer renglón.
        for row in lines(first_page)[:4]:
            folded = _norm_words(row)
            for i, word in enumerate(folded):
                if word in CLASSES and i > 0:
                    sheet.name = sheet.name or " ".join(w.text for w in row[:i])
                    class_text = class_text or " ".join(w.text for w in row[i:])
                    break
            if class_text:
                break
    if sheet.name.isupper():
        sheet.name = sheet.name.title()
    classes, subclass, level = parse_class_level(class_text)
    sheet.char_class, sheet.subclass, sheet.level = classes, subclass, level
    sheet.race = layout.label_value(HEADER_LABELS["race"])
    sheet.background = layout.label_value(HEADER_LABELS["background"])
    sheet.alignment = layout.label_value(HEADER_LABELS["alignment"])
    sheet.player_name = layout.label_value(HEADER_LABELS["player"])
    sheet.xp = to_int(layout.label_value(HEADER_LABELS["xp"])) or 0
    languages = layout.label_value(HEADER_LABELS["languages"])
    sheet.languages = [x.strip().capitalize() for x in languages.split(",") if x.strip()]
    sheet.speed_ft = parse_speed(layout.label_value(HEADER_LABELS["speed"]))


# --------------------------------------------------------------- características ---
def _abilities(layout: Layout, sheet: ParsedSheet) -> None:
    for word in sorted((w for w in layout.words if w.page == 0), key=lambda w: (w.cy, w.x0)):
        key = ABILITY_NAMES.get(fold(word.text))
        if key is None or key in sheet.abilities:
            continue
        for score in layout.near_all(word, right=60, below=45, width=40, pattern=UNSIGNED_RE)[:3]:
            value = int(score.text)
            if not 1 <= value <= 30:
                continue
            modifier = layout.near(score, right=40, above=40, below=40, width=40)
            if modifier is not None and to_int(modifier.text) != ability_modifier(value):
                continue  # el número no es una puntuación (p. ej. un bonificador sin signo)
            sheet.abilities[key] = value
            break


# ------------------------------------------------------------ habilidades y TS ---
def _skills_and_saves(layout: Layout, sheet: ParsedSheet) -> None:
    used: set[int] = set()
    for row in layout.rows:
        folded = _norm_words(row)
        i = 0
        while i < len(row):
            match = None
            for size in (4, 3, 2, 1):
                key = SKILL_NAMES.get(" ".join(folded[i : i + size]))
                if key and i + size <= len(row):
                    match = (key, size)
                    break
            if not match:
                i += 1
                continue
            key, size = match
            anchor = row[i]
            last = row[i + size - 1]
            text = " ".join(w.text for w in row[i : i + size])
            probe = Word(text, anchor.x0, anchor.y0, last.x1, last.y1, anchor.page)
            value = layout.near(probe, right=90, below=16, width=45, exclude=used)
            if value is not None and key not in sheet.skill_bonus:
                used.add(id(value))
                sheet.skill_bonus[key] = to_int(value.text) or 0
            i += size
    heading = layout.phrase_anchor(["tiradas de salvacion", "saving throws"])
    if heading is None:
        return
    for direction in ("below", "above"):
        found: dict[str, int] = {}
        for word in layout.words:
            key = ABILITY_NAMES.get(fold(word.text))
            if key is None or word.page != heading.page:
                continue
            dy = word.cy - heading.cy
            if (direction == "below" and not 0 < dy < 110) or (direction == "above" and not -110 < dy < 0):
                continue
            if abs(word.x0 - heading.x0) > 220:
                continue
            value = layout.near(word, right=100)
            if value is not None:
                found.setdefault(key, to_int(value.text) or 0)
        if len(found) >= 4:
            sheet.save_bonus = found
            return


# ----------------------------------------------------------------------- combate ---
def _value_near_label(layout: Layout, labels: list[str], pattern: re.Pattern[str]) -> str | None:
    for row in layout.rows:
        for label in labels:
            found = _find_phrase(row, label)
            if not found:
                continue
            start, end = found
            anchor = Word(" ".join(w.text for w in row[start:end]), row[start].x0, row[start].y0,
                          row[end - 1].x1, row[end - 1].y1, row[start].page)
            hit = layout.near(anchor, right=70, below=30, above=26, width=45, pattern=pattern)
            if hit is not None:
                return hit.text
    return None


def _combat(layout: Layout, sheet: ParsedSheet) -> None:
    number = re.compile(r"^\d{1,3}$")
    hp = _value_near_label(layout, ["puntos de golpe maximos", "hit point maximum", "max hp", "puntos de golpe"],
                           number)
    sheet.hp_max = int(hp) if hp else None
    ac = _value_near_label(layout, ["clase de armadura", "armor class", "ca"], number)
    sheet.armor_class = int(ac) if ac else None
    prof = _value_near_label(layout, ["bonificador de competencia", "competencia", "proficiency bonus"],
                             re.compile(r"^\+\d$"))
    sheet.proficiency = to_int(prof) if prof else None
    if sheet.speed_ft is None:
        speed = _value_near_label(layout, ["velocidad", "speed"], number)
        sheet.speed_ft = int(speed) if speed else None
    dice = _value_near_label(layout, ["dados de golpe", "hit dice", "total"], re.compile(r"^\d+[dD]\d+$"))
    die = re.search(r"[dD](4|6|8|10|12)$", dice or "")
    if die:
        sheet.hit_die = f"d{die.group(1)}"
    flat = " ".join(layout.text_lines())
    darkvision = re.search(r"(?:darkvision|visi[oó]n en la oscuridad)[^\d]{0,400}?(\d{2,3})\s*(?:pies|ft|feet)", flat,
                           re.IGNORECASE)
    if darkvision:
        sheet.darkvision_ft = int(darkvision.group(1))
    for match in re.finditer(r"(?:resistencia|resistance)[^.]{0,80}", flat, re.I):
        folded = fold(match.group(0))
        sheet.resistances += [key for word, key in DAMAGE_TYPES.items() if re.search(rf"\b{word}\b", folded)
                              and key != "force"]


# ----------------------------------------------------------------------- ataques ---
NAME = r"(?:^|(?<=\s))(?P<name>[A-Za-zÁÉÍÓÚÑáéíóúñ][^\d+\-]{1,39}?)"
ATTACK_RES = [
    re.compile(NAME + r"\s+(?P<bonus>[+\-]\d{1,2})\s+a impactar\.?\s+(?P<damage>\d+d\d+(?:\s*[+\-]\s*\d+)?)"
               r"\s+de da[nñ]o\s+(?P<type>\w+)(?P<notes>.*)$", re.IGNORECASE),
    re.compile(NAME + r"\s+(?P<bonus>[+\-]\d{1,2})\s+(?P<damage>\d+d\d+(?:\s*[+\-]\s*\d+)?)"
               r"\s+(?P<type>[A-Za-záéíóúñ]+)(?P<notes>.*)$"),
]


def _attacks(layout: Layout, sheet: ParsedSheet) -> None:
    for line in layout.text_lines():
        for pattern in ATTACK_RES:
            match = pattern.search(line.strip())
            if not match:
                continue
            name = match.group("name").strip()
            if fold(name) in {"nombre", "name"} or len(name.split()) > 6:
                continue
            damage = f"{match.group('damage')} {match.group('type')}"
            sheet.attacks.append(attack_from(name.capitalize(), to_int(match.group("bonus")), damage, sheet,
                                             match.group("notes")))
            break


# ----------------------------------------------------------------------- conjuros ---
SPELL_LINE = re.compile(r"^(?P<name>[A-ZÁÉÍÓÚÑ][^·]{1,50}?)\s+(?:Nivel\s+(?P<level>\d)|Level\s+(?P<level_en>\d)|"
                        r"(?P<cantrip>Truco|Cantrip))\s*·", re.IGNORECASE)
SLOT_LINE = re.compile(r"^(?:Nivel|Level)\s+(\d)\s*·\s*(\d+)\s*$", re.IGNORECASE)
SCHOOLS = ("abjuracion|conjuracion|adivinacion|encantamiento|evocacion|ilusion|nigromancia|transmutacion|"
           "abjuration|conjuration|divination|enchantment|evocation|illusion|necromancy|transmutation")
SCHOOL_RE = re.compile(SCHOOLS)


def _spell_row(texts: list[str]) -> tuple[str, int] | None:
    """Fila de tabla «nivel/Truco  Nombre  Escuela ...» -> (nombre, nivel)."""
    for index, text in enumerate(texts):
        if not SCHOOL_RE.fullmatch(fold(text)):
            continue
        for start in range(index - 1, -1, -1):
            token = texts[start]
            if token in ("Truco", "Cantrip") or re.fullmatch(r"[1-9]", token):
                name = " ".join(texts[start + 1:index]).strip()
                name = re.sub(r"\s+(?:y|and|de|del|of)$", "", name)
                if 2 <= len(name) <= 60 and name[0].isupper():
                    return name, 0 if token in ("Truco", "Cantrip") else int(token)
                return None
        return None
    return None
CASTER_ABILITY = {
    "paladin": "cha", "bardo": "cha", "brujo": "cha", "hechicero": "cha", "bard": "cha", "warlock": "cha",
    "sorcerer": "cha", "clerigo": "wis", "druida": "wis", "explorador": "wis", "cleric": "wis", "druid": "wis",
    "ranger": "wis", "mago": "int", "artifice": "int", "wizard": "int", "artificer": "int",
}


def _spells(layout: Layout, sheet: ParsedSheet) -> None:
    anchor = layout.phrase_anchor(["caracteristica cd de salvacion", "spellcasting ability"])
    if anchor is not None:
        for word in layout.words:
            if word.page == anchor.page and 2 < word.cy - anchor.cy < 25 and abs(word.x0 - anchor.x0) < 60:
                key = ABILITY_NAMES.get(fold(word.text))
                if key:
                    sheet.spellcasting_ability = key
                    break
    seen: set[str] = set()
    for line in layout.text_lines():
        slot = SLOT_LINE.match(line.strip())
        if slot:
            sheet.spell_slots[slot.group(1)] = {"max": int(slot.group(2)), "used": 0}
            continue
        match = SPELL_LINE.match(line.strip())
        if match and match.group("name") not in seen:
            level = 0 if match.group("cantrip") else int(match.group("level") or match.group("level_en") or 0)
            seen.add(match.group("name"))
            sheet.spells.append({"name": match.group("name").strip(), "level": level, "prepared": True,
                                 "description": ""})
            continue
    for row in layout.raw_rows:
        spell = _spell_row([w.text for w in row])
        if spell and spell[0] not in seen:
            seen.add(spell[0])
            sheet.spells.append({"name": spell[0], "level": spell[1], "prepared": True, "description": ""})
    if sheet.spells and not sheet.spellcasting_ability:
        first_class = fold(sheet.char_class.split("/")[0]).split(" ")[0] if sheet.char_class else ""
        sheet.spellcasting_ability = CASTER_ABILITY.get(first_class)


# ----------------------------------------------------------------- rasgos y texto ---
def _features(layout: Layout, sheet: ParsedSheet) -> None:
    names: list[str] = []
    for row in layout.rows:
        text = " ".join(w.text for w in row)
        has_icon = any(g.page == row[0].page and abs(g.cy - row[0].cy) < 6 and g.x1 <= row[0].x0 + 2
                       for g in layout.glyphs)
        title = re.match(r"^([A-ZÁÉÍÓÚÑ][\wáéíóúñü' ]{2,40}):", text)
        if has_icon and title:
            names.append(title.group(1).strip())
        elif re.match(r"^-\s+[A-ZÁÉÍÓÚÑ]", text) and len(text) < 60:
            names.append(text[1:].strip())
    for name in dict.fromkeys(names):
        if fold(name) not in {"ideales", "vinculos", "defectos", "ideals", "bonds", "flaws"}:
            sheet.features.append({"name": name[:80], "description": "", "uses_max": None, "uses_used": 0})
    personality = [t for t in layout.text_lines() if re.match(r"^(Ideales|Vínculos|Defectos|Ideals|Bonds|Flaws):", t)]
    sheet.personality = "\n".join(personality)[:2000]
