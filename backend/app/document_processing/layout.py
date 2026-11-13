"""Orden de lectura de una página: respeta maquetaciones a dos columnas (típicas de aventuras de 5e)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class HasBBox(Protocol):
    @property
    def bbox(self) -> tuple[float, float, float, float]: ...


def reading_order[T: HasBBox](blocks: Sequence[T], page_width: float) -> list[T]:
    """Ordena bloques: columna izquierda y luego derecha, cortando en los bloques que ocupan todo el ancho.

    Si la página no parece tener dos columnas se devuelve el orden de arriba abajo de siempre.
    """
    by_top = sorted(blocks, key=lambda b: (round(b.bbox[1], 1), b.bbox[0]))
    middle = page_width / 2
    margin = page_width * 0.06

    def spans_gutter(block: T) -> bool:
        return block.bbox[0] < middle - margin and block.bbox[2] > middle + margin

    left = [b for b in by_top if not spans_gutter(b) and (b.bbox[0] + b.bbox[2]) / 2 < middle]
    right = [b for b in by_top if not spans_gutter(b) and (b.bbox[0] + b.bbox[2]) / 2 >= middle]
    if len(left) < 2 or len(right) < 2:
        return by_top
    ordered: list[T] = []
    segment: list[T] = []

    def flush() -> None:
        ordered.extend(b for b in segment if (b.bbox[0] + b.bbox[2]) / 2 < middle)
        ordered.extend(b for b in segment if (b.bbox[0] + b.bbox[2]) / 2 >= middle)
        segment.clear()

    for block in by_top:
        if spans_gutter(block):
            flush()
            ordered.append(block)
        else:
            segment.append(block)
    flush()
    return ordered
