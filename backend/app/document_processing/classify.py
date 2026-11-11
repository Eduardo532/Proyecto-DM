"""Clasificación del contenido en público, condicionado o exclusivo del DM (D-03).

Principio: ante la duda, ``dm``. El DM puede corregir cualquier clasificación.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.engines.rules.abilities import SKILLS

STAT_BLOCK = re.compile(
    r"(armor class|clase de armadura|\bCA\s+\d+).{0,400}?(hit points|puntos de golpe|\bPG\s+\d+)",
    re.IGNORECASE | re.DOTALL,
)
DC_PATTERN = re.compile(r"\b(?:CD|DC)\s*(\d{1,2})\b")
SECRET_WORDS = re.compile(
    r"\b(secret[oa]?s?|ocult[oa]s?|escondid[oa]s?|trampa|trap|hidden|concealed|"
    r"si los personajes|if the characters|if a character|si un personaje|desarrollo|development|"
    r"tácticas|tactics|en realidad|in truth|actually)\b",
    re.IGNORECASE,
)
DM_WORDS = re.compile(
    r"\b(dungeon master|director de juego|\bDM\b|\bDJ\b|resumen de la aventura|adventure (summary|background)|"
    r"trasfondo de la aventura|notas para el|tesoro|treasure|experiencia|\bPX\b|\bXP\b)",
    re.IGNORECASE,
)
INJECTION = re.compile(
    r"(ignore (all |the )?(previous|above) instructions|ignora (todas )?las instrucciones|"
    r"you are (an? )?(ai|assistant|language model)|eres un (asistente|modelo)|system prompt)",
    re.IGNORECASE,
)



def fold(text: str) -> str:
    """Minúsculas y sin tildes, para comparar textos de PDF con o sin acentos."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


# Nombres de habilidades en español e inglés (sin tildes) -> identificador.
SKILL_NAMES: dict[str, str] = {}
for _skill, (_ability, _label) in SKILLS.items():
    SKILL_NAMES[fold(_label)] = _skill
    SKILL_NAMES[_skill.replace("_", " ")] = _skill
SKILL_NAMES.update({"arcanos": "arcana", "c. arcano": "arcana", "trato con animales": "animal_handling"})
SKILL_PATTERN = re.compile("|".join(sorted((re.escape(k) for k in SKILL_NAMES), key=len, reverse=True)), re.IGNORECASE)


@dataclass(frozen=True)
class Classification:
    kind: str
    level: str
    reason: str


@dataclass(frozen=True)
class Discovery:
    skill: str | None
    dc: int
    sentence: str


def classify(text: str, *, read_aloud: bool) -> Classification:
    if INJECTION.search(text):
        return Classification("narrative", "dm", "Contiene texto dirigido a una IA: revisar manualmente.")
    if STAT_BLOCK.search(text):
        return Classification("stat_block", "dm", "Bloque de estadísticas.")
    if read_aloud:
        return Classification("read_aloud", "public", "Texto para leer en voz alta.")
    if DC_PATTERN.search(text) or SECRET_WORDS.search(text):
        return Classification("narrative", "conditional", "Menciona pruebas, secretos o trampas.")
    if DM_WORDS.search(text):
        return Classification("narrative", "dm", "Información dirigida al DM.")
    return Classification("narrative", "dm", "Descripción sin marcar como pública (cerrado por defecto).")


def discoveries(text: str) -> list[Discovery]:
    """Frases con una CD (p. ej. 'una prueba de Sabiduría (Percepción) CD 15 revela...')."""
    found: list[Discovery] = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for index, sentence in enumerate(sentences):
        match = DC_PATTERN.search(sentence)
        if not match:
            continue
        skill_match = SKILL_PATTERN.search(fold(sentence))
        skill = SKILL_NAMES.get(skill_match.group(0)) if skill_match else None
        context = sentences[index - 1].strip() + " " if index > 0 and len(sentence) < 160 else ""
        found.append(Discovery(skill, int(match.group(1)), (context + sentence.strip())[:600]))
    return found


def player_text(statement: str) -> str:
    """Versión para la mesa: sin las referencias a pruebas y CD del texto del DM."""
    cleaned = re.sub(r"\s*\((?:[^()]*\b(?:CD|DC)\s*\d+[^()]*)\)", "", statement)
    cleaned = re.sub(r"\b(?:CD|DC)\s*\d+\b", "", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip()
