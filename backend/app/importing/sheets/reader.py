"""Punto de entrada: detecta el tipo de ficha y la lee con el lector adecuado."""

from __future__ import annotations

from pathlib import Path

from app.importing.pdftext import form_fields, page_words
from app.importing.sheets.fields import is_character_form, parse_fields
from app.importing.sheets.layout import parse_layout
from app.importing.sheets.model import ParsedSheet


def read_sheet(path: Path) -> ParsedSheet:
    fields = form_fields(path)
    if is_character_form(fields):
        sheet = parse_fields(fields)
    else:
        words, sizes = page_words(path, max_pages=8)
        text = " ".join(w.text for w in words[:400]).lower()
        fmt = "nivel20" if "nivel20" in " ".join(w.text.lower() for w in words) else "texto"
        if fmt == "texto" and ("hoja de personaje" in text or "nombre del personaje" in text):
            fmt = "hoja_es"
        sheet = parse_layout(words, [w for w, _ in sizes], fmt)
    if sheet.player_name:
        sheet.notes = f"Jugador original: {sheet.player_name}".strip()
    return sheet
