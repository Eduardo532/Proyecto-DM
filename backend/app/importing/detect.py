"""Reconoce qué es cada archivo importado: aventura, ficha de personaje, mapa, ilustración, token o marcador.

La decisión se toma por el contenido (campos de formulario, texto, tamaño y transparencia de la imagen,
cuadrícula) y se apoya en el nombre del archivo y de su carpeta. El DM puede corregirla después.
"""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from app.importing.maps import GRID_CONFIDENCE, clean_stem, estimate_grid, looks_like_map_name, variant_of
from app.importing.vocab import CONDITION_NAMES, fold

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
KINDS = ("adventure", "character", "map", "handout", "token", "marker", "archive", "ignored")
KIND_LABELS = {
    "adventure": "Aventura / módulo",
    "character": "Ficha de personaje",
    "map": "Mapa",
    "handout": "Ilustración / material para jugadores",
    "token": "Token",
    "marker": "Marcador de estado",
    "archive": "Archivo comprimido",
    "ignored": "Ignorado",
}
MARKER_NAME = re.compile(r"^\d{1,3}_+([A-Za-z][A-Za-z0-9 ]*)$")
MARKER_FOLDER = re.compile(r"\b(?:markers?|marcadores?|conditions?|condiciones|estados?|status)\b")
TOKEN_NAME = re.compile(r"\b(?:tokens?|fichas? de mapa|miniaturas?|minis?)\b")
IGNORED_NAME = re.compile(r"\b(?:logo|thumbs?|thumbnail|banner)\b")
HANDOUT_FOLDER = re.compile(r"\b(?:images?|imagenes|art|arte|illustrations?|ilustraciones|handouts?)\b")


@dataclass
class Detected:
    relative: str
    kind: str
    name: str
    reason: str
    group_key: str = ""
    variant: str = ""
    width: int = 0
    height: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


def detect_file(path: Path, relative: str) -> Detected:
    suffix = path.suffix.lower()
    folder = " ".join(PurePosixPath(relative).parts[:-1])
    original = PurePosixPath(relative).name or path.name  # en subidas sueltas el archivo guardado se renombra
    name = clean_stem(original)
    if suffix == ".zip":
        return Detected(relative, "archive", name, "Archivo ZIP.")
    if suffix == ".pdf":
        return _detect_pdf(path, relative, name)
    if suffix in IMAGE_EXTENSIONS:
        return _detect_image(path, relative, name, folder, original)
    return Detected(relative, "ignored", name, f"Tipo de archivo no compatible ({suffix or 'sin extensión'}).")


# ------------------------------------------------------------------------- PDF ---
def _detect_pdf(path: Path, relative: str, name: str) -> Detected:
    from app.importing.pdftext import form_fields
    from app.importing.sheets.fields import is_character_form
    from app.importing.sheets.reader import read_sheet

    try:
        pages, words, coverage = pdf_profile(path)
        is_form = is_character_form(form_fields(path))
        # Una ficha tiene pocas páginas; un libro largo sin formulario de personaje es una aventura.
        sheet = read_sheet(path) if is_form or pages <= 12 else None
    except Exception as exc:  # PDF dañado o cifrado
        return Detected(relative, "ignored", name, f"No se pudo leer el PDF ({exc}).")
    if sheet is not None and sheet.confidence() >= 0.6 and (is_form or (sheet.name and sheet.char_class)):
        labels = {"dndbeyond": "D&D Beyond", "wotc_form": "hoja oficial rellenable", "nivel20": "Nivel20",
                  "hoja_es": "hoja en español", "texto": "texto"}
        return Detected(relative, "character", sheet.name or name,
                        f"Ficha de personaje ({labels.get(sheet.format, sheet.format)}).",
                        meta={"format": sheet.format, "confidence": round(sheet.confidence(), 2)})
    if pages <= 4 and words < 80 * pages and coverage > 0.5:
        return Detected(relative, "map", name, "PDF de una imagen a página completa con poco texto (mapa).",
                        group_key=variant_of(name)[0], variant=variant_of(name)[1], meta={"pdf": True})
    return Detected(relative, "adventure", name, f"Documento de texto de {pages} páginas (aventura o suplemento).")


def pdf_profile(path: Path, max_pages: int = 4) -> tuple[int, int, float]:
    """(páginas, palabras en las primeras páginas, mayor fracción de página cubierta por una imagen)."""
    try:
        pymupdf: Any = importlib.import_module("pymupdf")
        doc: Any = pymupdf.open(path)
        pages = doc.page_count
        words, coverage = 0, 0.0
        for index in range(min(pages, max_pages)):
            page = doc[index]
            words += len(page.get_text("words"))
            area = page.rect.width * page.rect.height or 1
            for info in page.get_images(full=True):
                for rect in page.get_image_rects(info[0]):
                    coverage = max(coverage, rect.width * rect.height / area)
        doc.close()
        return pages, words, coverage
    except ImportError:  # pragma: no cover - entorno de desarrollo sin PyMuPDF
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            pages = len(pdf.pages)
            words, coverage = 0, 0.0
            for page in pdf.pages[:max_pages]:
                words += len(page.extract_words())
                area = float(page.width * page.height) or 1.0
                for image in page.images:
                    width, height = float(image["x1"] - image["x0"]), float(image["bottom"] - image["top"])
                    coverage = max(coverage, width * height / area)
            return pages, words, coverage


# --------------------------------------------------------------------- imágenes ---
def _image_info(path: Path) -> tuple[int, int, bool] | None:
    from PIL import Image

    try:
        with Image.open(path) as image:
            width, height = image.size
            transparent = False
            if image.mode in ("RGBA", "LA", "P"):
                rgba = image.convert("RGBA")
                corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
                alphas = [rgba.getpixel(c) for c in corners]
                transparent = sum(1 for p in alphas if isinstance(p, tuple) and p[3] < 16) >= 3
            return width, height, transparent
    except (OSError, ValueError):
        return None


def _detect_image(path: Path, relative: str, name: str, folder: str, original: str) -> Detected:
    info = _image_info(path)
    if info is None:
        return Detected(relative, "ignored", name, "La imagen no se puede abrir.")
    width, height, transparent = info
    stem = PurePosixPath(original).stem
    folded_name, folded_folder = fold(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)), fold(folder)
    squareish = abs(width - height) <= 0.15 * max(width, height)

    def make(kind: str, reason: str, **extra: Any) -> Detected:
        return Detected(relative, kind, name, reason, width=width, height=height, **extra)

    if IGNORED_NAME.search(folded_name) and max(width, height) < 1600:
        return make("ignored", "Logotipo o miniatura.")
    marker = MARKER_NAME.match(stem)
    if (marker or MARKER_FOLDER.search(folded_folder)) and squareish and max(width, height) <= 1024:
        label = marker.group(1) if marker else name
        label_words = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", label).strip()
        condition = CONDITION_NAMES.get(fold(label).replace(" ", ""))
        reason = "Marcador de estado" + (f" ({condition})." if condition else ".")
        result = make("marker", reason, meta={"label": label_words, "condition": condition,
                                               "set": PurePosixPath(relative).parent.as_posix()})
        result.name = label_words
        return result
    if (TOKEN_NAME.search(folded_name) or TOKEN_NAME.search(folded_folder) or transparent) and squareish \
            and max(width, height) <= 1024:
        return make("token", "Imagen pequeña y cuadrada" + (" con fondo transparente." if transparent else "."))
    group_key, variant = variant_of(original)
    if looks_like_map_name(original, folder):
        return make("map", "El nombre indica que es un mapa.", group_key=group_key, variant=variant)
    if min(width, height) >= 500 and not HANDOUT_FOLDER.search(folded_folder):
        guess = estimate_grid(path)
        if guess is not None and guess.confidence >= GRID_CONFIDENCE:
            return make("map", f"Se detecta una cuadrícula de {guess.cell_w:g} x {guess.cell_h:g} px.",
                        group_key=group_key, variant=variant)
    return make("handout", "Ilustración (sin cuadrícula ni nombre de mapa).")
