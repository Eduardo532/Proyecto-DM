"""Lectura de PDF común a todos los importadores: palabras con posición y campos de formulario.

Producción: PyMuPDF (palabras) y pypdf (campos). En desarrollo, si PyMuPDF no está instalado, se usa
pdfplumber para las palabras.
"""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


DOUBLED = re.compile(r"^(?:(.)\1)+$", re.DOTALL)
ICON = re.compile(r"([\ue000-\uf8ff]+)")


def split_icons(text: str, x0: float, y0: float, x1: float, y1: float, page: int) -> list[Word]:
    """Separa los iconos de fuentes de símbolos pegados al texto («xx\uf10cMedicina»)."""
    if not ICON.search(text):
        cleaned = undouble(text)
        return [Word(cleaned, x0, y0, x1, y1, page)] if cleaned.strip() else []
    result: list[Word] = []
    width = (x1 - x0) / max(1, len(text))
    position = 0
    for part in ICON.split(text):
        if not part:
            continue
        start = x0 + position * width
        position += len(part)
        if ICON.fullmatch(part):
            result.append(Word(part, start, y0, start + width * len(part), y1, page))
        else:
            cleaned = undouble(re.sub(r"^x{1,2}$", "", part))
            if cleaned.strip():
                result.append(Word(cleaned, start, y0, start + width * len(part), y1, page))
    return result


def undouble(text: str) -> str:
    """Algunos PDF dibujan cada letra dos veces para simular negrita: «TTiieefflliinngg» → «Tiefling»."""
    if len(text) >= 4 and len(text) % 2 == 0 and DOUBLED.match(text):
        return text[::2]
    if len(text) == 2 and text[0] == text[1] and text.islower():
        return text[0]
    return text


def page_words(path: Path, max_pages: int = 50) -> tuple[list[Word], list[tuple[float, float]]]:
    """Palabras de cada página y tamaño (ancho, alto) de las páginas."""
    try:
        pymupdf: Any = importlib.import_module("pymupdf")  # tipado solo en parte: se trata como Any
    except ImportError:  # pragma: no cover - solo en entornos de desarrollo sin PyMuPDF
        return _words_pdfplumber(path, max_pages)
    words: list[Word] = []
    sizes: list[tuple[float, float]] = []
    doc: Any = pymupdf.open(path)
    try:
        for index, page in enumerate(doc):
            if index >= max_pages:
                break
            sizes.append((float(page.rect.width), float(page.rect.height)))
            for x0, y0, x1, y1, text, *_ in page.get_text("words"):
                words.extend(split_icons(str(text), float(x0), float(y0), float(x1), float(y1), index))
    finally:
        doc.close()
    return words, sizes


def _words_pdfplumber(path: Path, max_pages: int) -> tuple[list[Word], list[tuple[float, float]]]:  # pragma: no cover
    import pdfplumber

    words: list[Word] = []
    sizes: list[tuple[float, float]] = []
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages[:max_pages]):
            sizes.append((float(page.width), float(page.height)))
            for w in page.extract_words():
                words.extend(split_icons(str(w["text"]), w["x0"], w["top"], w["x1"], w["bottom"], index))
    return words, sizes


def form_fields(path: Path) -> list[tuple[str, str, int]]:
    """Campos de formulario en orden de aparición: (nombre, valor, página).

    Lee los widgets de cada página directamente, porque algunos exportadores (p. ej. D&D Beyond) dejan
    los campos fuera del formulario del documento.
    """
    import pypdf

    fields: list[tuple[str, str, int]] = []
    try:
        reader = pypdf.PdfReader(str(path))
    except Exception:
        return fields
    for page_index, page in enumerate(reader.pages):
        annots = page.get("/Annots")
        if annots is None:
            continue
        for ref in annots.get_object():
            annot = ref.get_object()
            if annot.get("/Subtype") != "/Widget":
                continue
            name = annot.get("/T")
            parent = annot.get("/Parent")
            value = annot.get("/V")
            while (name is None or value is None) and parent is not None:
                parent_obj = parent.get_object()
                name = name if name is not None else parent_obj.get("/T")
                value = value if value is not None else parent_obj.get("/V")
                parent = parent_obj.get("/Parent")
            if name is None:
                continue
            text = str(value) if value is not None else ""
            if text in {"/Off", "Off"}:
                text = ""
            if text.startswith("/"):
                text = text[1:]  # casillas marcadas: /Yes, /On
            fields.append((str(name), text, page_index))
    return fields


def lines(words: list[Word], tolerance: float = 3.0) -> list[list[Word]]:
    """Agrupa palabras en renglones (misma página y altura parecida), de izquierda a derecha."""
    ordered = sorted(words, key=lambda w: (w.page, w.cy, w.x0))
    rows: list[list[Word]] = []
    for word in ordered:
        if rows and rows[-1][0].page == word.page and abs(rows[-1][0].cy - word.cy) <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: w.x0) for row in rows]


def undouble_line(text: str) -> str:
    """Deshace el «falso negrita» en una línea completa solo si la mayoría de sus palabras está duplicada."""
    words = text.split()
    doubled = [w for w in words if len(w) >= 2 and len(w) % 2 == 0 and DOUBLED.match(w)]
    if not words or not any(len(w) >= 4 for w in doubled) or len(doubled) < 0.6 * len(words):
        return text
    return " ".join(w[::2] if w in doubled else w for w in words)
