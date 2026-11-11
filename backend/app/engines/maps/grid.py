"""Cuadrícula lógica de un mapa.

Coordenadas: ``x`` = columna (0 a la izquierda), ``y`` = fila (0 arriba).
Etiqueta visible: columna en letras y fila en número, p. ej. ``C7``.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import pairwise

from app.engines.errors import RuleViolation

Cell = tuple[int, int]


class Terrain(StrEnum):
    FLOOR = "floor"
    WALL = "wall"
    DIFFICULT = "difficult"
    WATER = "water"
    PIT = "pit"
    VOID = "void"


BLOCKS_MOVEMENT = {Terrain.WALL, Terrain.VOID, Terrain.PIT}
BLOCKS_SIGHT = {Terrain.WALL}


class DoorState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"


def column_label(x: int) -> str:
    label = ""
    x += 1
    while x:
        x, rem = divmod(x - 1, 26)
        label = chr(65 + rem) + label
    return label


def cell_label(cell: Cell) -> str:
    return f"{column_label(cell[0])}{cell[1] + 1}"


@dataclass
class Grid:
    width: int
    height: int
    cell_size_ft: int = 5
    terrain: dict[Cell, Terrain] = field(default_factory=dict)
    doors: dict[Cell, DoorState] = field(default_factory=dict)
    diagonal_rule: str = "5e"  # "5e" (todas 5 pies) o "5-10-5" (variante del DMG)

    def __post_init__(self) -> None:
        if not (1 <= self.width <= 200 and 1 <= self.height <= 200):
            raise RuleViolation("El mapa debe medir entre 1 y 200 casillas por lado.")

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.width and 0 <= cell[1] < self.height

    def terrain_at(self, cell: Cell) -> Terrain:
        return self.terrain.get(cell, Terrain.FLOOR)

    def blocks_movement(self, cell: Cell) -> bool:
        if not self.in_bounds(cell) or self.terrain_at(cell) in BLOCKS_MOVEMENT:
            return True
        return self.doors.get(cell) in {DoorState.CLOSED, DoorState.LOCKED}

    def blocks_sight(self, cell: Cell) -> bool:
        if not self.in_bounds(cell) or self.terrain_at(cell) in BLOCKS_SIGHT:
            return True
        return self.doors.get(cell) in {DoorState.CLOSED, DoorState.LOCKED}

    def neighbors(self, cell: Cell) -> Iterator[Cell]:
        x, y = cell
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    nxt = (x + dx, y + dy)
                    if self.in_bounds(nxt):
                        yield nxt

    def distance_ft(self, a: Cell, b: Cell) -> int:
        dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
        if self.diagonal_rule == "5-10-5":
            diagonals = min(dx, dy)
            straight = max(dx, dy) - diagonals
            return (straight + diagonals + diagonals // 2) * self.cell_size_ft
        return max(dx, dy) * self.cell_size_ft

    def step_cost_ft(self, frm: Cell, to: Cell, diagonal_parity: int = 0) -> int:
        base = self.cell_size_ft
        is_diagonal = frm[0] != to[0] and frm[1] != to[1]
        if self.diagonal_rule == "5-10-5" and is_diagonal and diagonal_parity % 2 == 1:
            base *= 2
        if self.terrain_at(to) in {Terrain.DIFFICULT, Terrain.WATER}:
            base *= 2
        return base

    def _corner_cut(self, frm: Cell, to: Cell) -> bool:
        """No se puede pasar en diagonal entre dos paredes que se tocan por la esquina."""
        if frm[0] == to[0] or frm[1] == to[1]:
            return False
        return self.blocks_movement((to[0], frm[1])) and self.blocks_movement((frm[0], to[1]))


@dataclass(frozen=True)
class Occupancy:
    """Casillas ocupadas por otras criaturas desde el punto de vista de quien se mueve."""

    hostile: frozenset[Cell] = frozenset()
    friendly: frozenset[Cell] = frozenset()


def reachable(
    grid: Grid, start: Cell, budget_ft: int, occupancy: Occupancy | None = None
) -> dict[Cell, int]:
    """Casillas alcanzables y su coste mínimo en pies (Dijkstra).

    Los hostiles bloquean el paso; los aliados se pueden atravesar pero no se puede terminar en su casilla.
    """
    occ = occupancy or Occupancy()
    best: dict[Cell, tuple[int, int]] = {start: (0, 0)}
    queue: list[tuple[int, int, Cell]] = [(0, 0, start)]
    while queue:
        cost, diagonals, cell = heapq.heappop(queue)
        if best.get(cell, (10**9, 0))[0] < cost:
            continue
        for nxt in grid.neighbors(cell):
            if grid.blocks_movement(nxt) or nxt in occ.hostile or grid._corner_cut(cell, nxt):
                continue
            is_diag = nxt[0] != cell[0] and nxt[1] != cell[1]
            parity = diagonals + 1 if is_diag else diagonals
            new_cost = cost + grid.step_cost_ft(cell, nxt, parity if is_diag else 0)
            if new_cost > budget_ft:
                continue
            if new_cost < best.get(nxt, (10**9, 0))[0]:
                best[nxt] = (new_cost, parity)
                heapq.heappush(queue, (new_cost, parity, nxt))
    return {c: v[0] for c, v in best.items() if c == start or c not in occ.friendly}


def path_cost(grid: Grid, path: Iterable[Cell], occupancy: Occupancy | None = None) -> int:
    """Valida un camino casilla a casilla y devuelve su coste en pies."""
    occ = occupancy or Occupancy()
    cells = list(path)
    if len(cells) < 2:
        return 0
    total = 0
    diagonals = 0
    for frm, to in pairwise(cells):
        if max(abs(frm[0] - to[0]), abs(frm[1] - to[1])) != 1:
            raise RuleViolation(f"El camino salta de {cell_label(frm)} a {cell_label(to)}.")
        if grid.blocks_movement(to) or grid._corner_cut(frm, to):
            raise RuleViolation(f"No se puede pasar por {cell_label(to)}.")
        if to in occ.hostile:
            raise RuleViolation(f"Una criatura hostil ocupa {cell_label(to)}.")
        is_diag = frm[0] != to[0] and frm[1] != to[1]
        if is_diag:
            diagonals += 1
        total += grid.step_cost_ft(frm, to, diagonals if is_diag else 0)
    if cells[-1] in occ.friendly:
        raise RuleViolation(f"No se puede terminar el movimiento en {cell_label(cells[-1])}: está ocupada.")
    return total


def shortest_path(
    grid: Grid, start: Cell, goal: Cell, occupancy: Occupancy | None = None
) -> list[Cell] | None:
    """Camino más barato entre dos casillas, o ``None`` si no existe."""
    occ = occupancy or Occupancy()
    queue: list[tuple[int, Cell]] = [(0, start)]
    came: dict[Cell, Cell | None] = {start: None}
    cost: dict[Cell, int] = {start: 0}
    while queue:
        current_cost, cell = heapq.heappop(queue)
        if cell == goal:
            break
        for nxt in grid.neighbors(cell):
            if grid.blocks_movement(nxt) or nxt in occ.hostile or grid._corner_cut(cell, nxt):
                continue
            new_cost = current_cost + grid.step_cost_ft(cell, nxt)
            if new_cost < cost.get(nxt, 10**9):
                cost[nxt] = new_cost
                came[nxt] = cell
                heapq.heappush(queue, (new_cost, nxt))
    if goal not in came:
        return None
    path: list[Cell] = []
    node: Cell | None = goal
    while node is not None:
        path.append(node)
        node = came[node]
    return path[::-1]
