"""Mapas importados: variantes (DM / jugadores / con o sin cuadrícula / zonas) y detección de la cuadrícula.

La cuadrícula se estima por autocorrelación de los bordes en cada eje por separado, porque muchos mapas
publicados tienen casillas rectangulares (por ejemplo 70 x 59 px) y no siempre empiezan en el píxel 0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from app.importing.vocab import fold

MAP_NAME = re.compile(
    r"\b(?:map|maps|mapa|mapas|battle ?map|battlemap|plano|planos|floor|planta|piso|dungeon|mazmorra|"
    r"encounter|encuentro|grid|gridded|cuadricula|level \d+|nivel \d+)\b"
)
VARIANT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("dm", re.compile(r"\b(?:mapa? (?:del|de los|para|for) )?(?:dm|gm|dj|master|director|keyed|secret|secretos)"
                      r"(?: version| map| mapa)?\b")),
    ("player", re.compile(r"\b(?:mapa? (?:del|de los|para|for) )?(?:players?|jugador(?:es)?|unkeyed|handout)"
                          r"(?: version| map| mapa)?\b")),
    ("nogrid", re.compile(r"\b(?:(?:no|without|sin) (?:grid|cuadricula)|gridless|nogrid)\b")),
    ("grid", re.compile(r"\b(?:(?:with|con) (?:grid|cuadricula)|gridded|grid)\b")),
    ("zones", re.compile(r"\b(?:(?:with|con) )?(?:zones|zonas)\b")),
]
PRODUCT_PREFIX = re.compile(r"^\d{4,}[-_ ]+")


def clean_stem(name: str) -> str:
    """Nombre legible a partir del nombre de archivo («446954-Player_Map_-_Floor_1.png» → «Player Map - Floor 1»)."""
    stem = PRODUCT_PREFIX.sub("", Path(name).stem)
    stem = re.sub(r"[_]+", " ", stem)
    return re.sub(r"\s+", " ", stem).strip(" -") or Path(name).stem


def variant_of(name: str) -> tuple[str, str]:
    """(clave de grupo, variante). Los archivos con la misma clave son versiones del mismo mapa."""
    key = fold(clean_stem(name))
    variant = "default"
    for label, pattern in VARIANT_PATTERNS:
        if pattern.search(key):
            if variant == "default":
                variant = label
            key = pattern.sub(" ", key)
    key = re.sub(r"\b(?:version|v\d+)\b", " ", key)
    return re.sub(r"\s+", " ", key).strip(), variant


def display_name(name: str) -> str:
    """Nombre del mapa sin las palabras de variante («Outpost Landing Map DM Version» → «Outpost Landing Map»)."""
    text = clean_stem(name)
    for _, pattern in VARIANT_PATTERNS:
        text = re.sub(pattern.pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:version|versión|v\d+)\b", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip(" -_") or clean_stem(name)


def looks_like_map_name(name: str, folder: str = "") -> bool:
    return bool(MAP_NAME.search(fold(clean_stem(name))) or MAP_NAME.search(fold(folder)))


# ------------------------------------------------------------------ cuadrícula ---
@dataclass
class GridGuess:
    cell_w: float
    cell_h: float
    offset_x: float
    offset_y: float
    confidence: float

    @property
    def square(self) -> bool:
        return abs(self.cell_w - self.cell_h) < 0.5


def _edge_profile(gray: NDArray[np.float32], axis: int) -> NDArray[np.float32]:
    """Intensidad media de los bordes a lo largo de un eje (picos donde hay líneas de cuadrícula)."""
    diff = np.abs(np.diff(gray, axis=axis))
    profile = np.asarray(diff.mean(axis=0) if axis == 1 else diff.mean(axis=1), dtype=np.float64)
    window = min(31, max(3, len(profile) // 20) | 1)
    trend = np.convolve(profile, np.ones(window) / window, mode="same")
    return np.clip(profile - trend, 0, None).astype(np.float32)


def _autocorrelation(profile: NDArray[np.float32]) -> NDArray[np.float64]:
    size = len(profile)
    spectrum = np.fft.rfft(profile, size * 2)
    result = np.asarray(np.fft.irfft(spectrum * np.conj(spectrum))[:size], dtype=np.float64)
    return result / (result[0] or 1.0)


def _period(profile: NDArray[np.float32], low: int, high: int) -> tuple[float, float]:
    """Periodo fundamental (con decimales) y su fuerza 0..1."""
    ac = _autocorrelation(profile)
    high = min(high, len(ac) // 3)
    if high <= low:
        return 0.0, 0.0
    lags = np.arange(low, high)
    best = int(lags[np.argmax(ac[lags])])
    # Un pico en 2x o 3x el periodo real también es fuerte: quedarse con el fundamental.
    reduced = True
    while reduced:
        reduced = False
        for divisor in (2, 3):
            candidate = best / divisor
            if candidate < low:
                continue
            near = range(max(low, int(candidate) - 1), int(candidate) + 2)
            peak = max(near, key=lambda lag: ac[lag])
            if ac[peak] > 0.75 * ac[best]:
                best, reduced = peak, True
                break
    strength = float(ac[best])
    # Precisión subpíxel: buscar el pico cerca de un múltiplo alto del periodo y dividir.
    multiple = max(1, int((len(ac) // 2) / best))
    if multiple > 1:
        center = best * multiple
        window = range(max(1, center - multiple - 1), min(len(ac) - 1, center + multiple + 2))
        peak = max(window, key=lambda lag: ac[lag])
        if ac[peak] > 0.5 * strength:
            return peak / multiple, strength
    return float(best), strength


def _phase(profile: NDArray[np.float32], period: float) -> float:
    steps = round(period)
    if steps < 2:
        return 0.0
    count = int(len(profile) / period)
    scores = []
    for offset in range(steps):
        positions = np.round(offset + np.arange(count) * period).astype(int)
        positions = positions[positions < len(profile)]
        scores.append(float(profile[positions].mean()) if len(positions) else 0.0)
    return float(int(np.argmax(scores)) % steps)


def _whole(size: int, cell: float) -> bool:
    count = size / cell if cell else 0
    return count >= 3 and abs(count - round(count)) < 0.08


def estimate_grid_array(gray: NDArray[np.float32], min_cell: int = 16, max_cell: int = 300) -> GridGuess:
    profile_x, profile_y = _edge_profile(gray, 1), _edge_profile(gray, 0)
    cell_w, strength_x = _period(profile_x, min_cell, max_cell)
    cell_h, strength_y = _period(profile_y, min_cell, max_cell)
    if cell_w and cell_h and abs(cell_w - cell_h) / max(cell_w, cell_h) < 0.04:
        cell_w = cell_h = (cell_w + cell_h) / 2
    confidence = min(strength_x, strength_y) if cell_w and cell_h else 0.0
    if confidence >= 0.2 and _whole(gray.shape[1], cell_w) and _whole(gray.shape[0], cell_h):
        # Los mapas con cuadrícula suelen medir un número entero de casillas: refuerza la estimación.
        confidence = min(1.0, confidence + 0.25)
    return GridGuess(
        cell_w=round(cell_w, 2), cell_h=round(cell_h, 2),
        offset_x=_phase(profile_x, cell_w) if cell_w else 0.0,
        offset_y=_phase(profile_y, cell_h) if cell_h else 0.0,
        confidence=round(max(0.0, confidence), 3),
    )


def estimate_grid(path: Path, max_side: int = 2400) -> GridGuess | None:
    """Cuadrícula de una imagen en píxeles de la imagen original. ``None`` si no se puede leer."""
    from PIL import Image

    try:
        with Image.open(path) as image:
            image.load()
            gray_image = image.convert("L")
    except (OSError, ValueError):
        return None
    scale = 1.0
    if max(gray_image.size) > max_side:
        scale = max_side / max(gray_image.size)
        gray_image = gray_image.resize((int(gray_image.width * scale), int(gray_image.height * scale)))
    guess = estimate_grid_array(np.asarray(gray_image, dtype=np.float32))
    if scale != 1.0:
        guess = GridGuess(round(guess.cell_w / scale, 2), round(guess.cell_h / scale, 2),
                          round(guess.offset_x / scale, 2), round(guess.offset_y / scale, 2), guess.confidence)
    return guess


def cells_for(width_px: int, height_px: int, cell_w: float, cell_h: float) -> tuple[int, int]:
    """Número de casillas (1..200) que cubren la imagen."""
    columns = round(width_px / cell_w) if cell_w > 0 else 1
    rows = round(height_px / cell_h) if cell_h > 0 else 1
    return max(1, min(200, columns)), max(1, min(200, rows))


DEFAULT_CELLS = 30
GRID_CONFIDENCE = 0.45


def fallback_cell(width_px: int, height_px: int) -> float:
    """Sin cuadrícula detectable: casillas cuadradas para que el lado largo tenga unas 30."""
    return max(10.0, max(width_px, height_px) / DEFAULT_CELLS)
