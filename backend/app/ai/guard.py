"""Filtro de fugas: comprueba que la narración no mencione secretos aún no revelados (capa 4 de D-03)."""

from __future__ import annotations

import re
import unicodedata

from app.models import Fact

COMMON = {
    "puerta", "pared", "suelo", "techo", "sala", "habitacion", "pasillo", "personaje", "personajes", "prueba",
    "secreta", "secreto", "oculta", "oculto", "trampa", "jugadores", "aventura", "the", "and", "una", "unos",
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def secret_terms(fact: Fact) -> set[str]:
    """Palabras que delatarían el secreto: palabras clave del hecho y nombres propios de su enunciado."""
    terms = {_norm(k) for k in fact.keywords if len(k) >= 3}
    for match in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,})", fact.statement):
        word = _norm(match.group(1))
        if word not in COMMON:
            terms.add(word)
    return terms


def leaks(text: str, unrevealed: list[Fact]) -> list[str]:
    normalized = _norm(text)
    found = []
    for fact in unrevealed:
        for term in secret_terms(fact):
            if re.search(rf"\b{re.escape(term)}\b", normalized):
                found.append(term)
    return sorted(set(found))
