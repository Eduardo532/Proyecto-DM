"""Línea de visión, iluminación, visión de criaturas y niebla de guerra."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from app.engines.maps.grid import Cell, Grid


class Light(IntEnum):
    DARK = 0
    DIM = 1
    BRIGHT = 2


@dataclass(frozen=True)
class LightSource:
    cell: Cell
    bright_ft: int
    dim_ft: int  # radio adicional de luz tenue más allá de la brillante


@dataclass(frozen=True)
class Viewer:
    cell: Cell
    darkvision_ft: int = 0
    blinded: bool = False
    max_range_ft: int = 600


def _line(a: Cell, b: Cell) -> list[Cell]:
    """Casillas atravesadas por la recta entre los centros de a y b (muestreo fino)."""
    (x0, y0), (x1, y1) = a, b
    steps = max(abs(x1 - x0), abs(y1 - y0)) * 4
    if steps == 0:
        return [a]
    cells: list[Cell] = []
    for i in range(steps + 1):
        t = i / steps
        cell = (round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t))
        if not cells or cells[-1] != cell:
            cells.append(cell)
    return cells


def has_line_of_sight(grid: Grid, a: Cell, b: Cell) -> bool:
    """Hay visión si ninguna casilla intermedia bloquea la vista (los extremos no cuentan)."""
    return all(not grid.blocks_sight(cell) for cell in _line(a, b)[1:-1])


def light_map(grid: Grid, sources: list[LightSource], ambient: Light) -> dict[Cell, Light]:
    levels: dict[Cell, Light] = {}
    for x in range(grid.width):
        for y in range(grid.height):
            levels[(x, y)] = ambient
    for source in sources:
        reach = (source.bright_ft + source.dim_ft) // grid.cell_size_ft
        sx, sy = source.cell
        for x in range(max(0, sx - reach), min(grid.width, sx + reach + 1)):
            for y in range(max(0, sy - reach), min(grid.height, sy + reach + 1)):
                cell = (x, y)
                dist = grid.distance_ft(source.cell, cell)
                if dist > source.bright_ft + source.dim_ft:
                    continue
                if cell != source.cell and not has_line_of_sight(grid, source.cell, cell):
                    continue
                level = Light.BRIGHT if dist <= source.bright_ft else Light.DIM
                if level > levels[cell]:
                    levels[cell] = level
    return levels


def visible_cells(grid: Grid, viewer: Viewer, lights: dict[Cell, Light]) -> set[Cell]:
    """Casillas que el observador puede ver ahora."""
    if viewer.blinded:
        return {viewer.cell}
    reach = viewer.max_range_ft // grid.cell_size_ft
    vx, vy = viewer.cell
    seen: set[Cell] = {viewer.cell}
    for x in range(max(0, vx - reach), min(grid.width, vx + reach + 1)):
        for y in range(max(0, vy - reach), min(grid.height, vy + reach + 1)):
            cell = (x, y)
            if cell == viewer.cell or not has_line_of_sight(grid, viewer.cell, cell):
                continue
            is_dark = lights.get(cell, Light.DARK) is Light.DARK
            if is_dark and grid.distance_ft(viewer.cell, cell) > viewer.darkvision_ft:
                continue
            seen.add(cell)
    return seen


@dataclass
class Fog:
    """Niebla de guerra de un observador o del grupo: visible ahora y explorado."""

    explored: set[Cell] = field(default_factory=set)
    visible: set[Cell] = field(default_factory=set)

    def update(self, visible: set[Cell]) -> None:
        self.visible = set(visible)
        self.explored |= visible

    def state(self, cell: Cell) -> str:
        if cell in self.visible:
            return "visible"
        if cell in self.explored:
            return "explored"
        return "unknown"


def group_visible(grid: Grid, viewers: list[Viewer], lights: dict[Cell, Light]) -> set[Cell]:
    """Visión de grupo (por defecto en pantalla compartida): unión de lo que ven todos."""
    seen: set[Cell] = set()
    for viewer in viewers:
        seen |= visible_cells(grid, viewer, lights)
    return seen
