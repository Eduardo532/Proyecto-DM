"""Imágenes sintéticas: mapas con y sin cuadrícula, ilustraciones, tokens y marcadores."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def _terrain(width: int, height: int, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = rng.normal(150, 18, (height // 8 + 1, width // 8 + 1, 3)).clip(0, 255).astype(np.uint8)
    image = Image.fromarray(base).resize((width, height), Image.Resampling.BICUBIC)
    draw = ImageDraw.Draw(image)
    for _ in range(12):  # «edificios» y caminos irregulares
        x, y = int(rng.integers(0, width - 80)), int(rng.integers(0, height - 80))
        draw.rectangle((x, y, x + int(rng.integers(30, 160)), y + int(rng.integers(30, 120))), fill=(90, 70, 50))
    return image


def battle_map(path: Path, width: int = 800, height: int = 600, cell: tuple[int, int] | None = (40, 30),
               offset: tuple[int, int] = (0, 0), seed: int = 1) -> Path:
    image = _terrain(width, height, seed)
    if cell is not None:
        draw = ImageDraw.Draw(image)
        for x in range(offset[0], width, cell[0]):
            draw.line((x, 0, x, height), fill=(30, 30, 30), width=1)
        for y in range(offset[1], height, cell[1]):
            draw.line((0, y, width, y), fill=(30, 30, 30), width=1)
    image.save(path)
    return path


def illustration(path: Path, width: int = 700, height: int = 900, seed: int = 7) -> Path:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:height, 0:width]
    red = 120 + 80 * np.sin(xx / 57.0 + yy / 91.0)
    green = 90 + 60 * np.cos(yy / 43.0)
    blue = rng.normal(110, 25, (height, width))
    pixels = np.stack([red, green, blue], axis=-1).clip(0, 255).astype(np.uint8)
    Image.fromarray(pixels).save(path)
    return path


def round_icon(path: Path, size: int = 128, color: tuple[int, int, int] = (180, 40, 40)) -> Path:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((4, 4, size - 4, size - 4), fill=(*color, 255))
    image.save(path)
    return path
