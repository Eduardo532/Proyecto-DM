import pytest

from app.engines.errors import RuleViolation
from app.engines.maps.grid import DoorState, Grid, Occupancy, Terrain, cell_label, path_cost, reachable, shortest_path
from app.engines.maps.vision import Fog, Light, LightSource, Viewer, has_line_of_sight, light_map, visible_cells


def room() -> Grid:
    """Sala 10x6 con una pared vertical en x=5 y una puerta en (5, 3)."""
    grid = Grid(10, 6)
    for y in range(6):
        grid.terrain[(5, y)] = Terrain.WALL
    grid.terrain[(5, 3)] = Terrain.FLOOR
    grid.doors[(5, 3)] = DoorState.CLOSED
    return grid


def test_etiquetas() -> None:
    assert cell_label((0, 0)) == "A1"
    assert cell_label((2, 6)) == "C7"
    assert cell_label((26, 0)) == "AA1"


def test_distancias() -> None:
    grid = Grid(20, 20)
    assert grid.distance_ft((0, 0), (3, 4)) == 20
    variant = Grid(20, 20, diagonal_rule="5-10-5")
    assert variant.distance_ft((0, 0), (2, 2)) == 15
    assert variant.distance_ft((0, 0), (4, 4)) == 30


def test_movimiento_con_terreno_dificil_y_ocupacion() -> None:
    grid = Grid(10, 10)
    grid.terrain[(1, 0)] = Terrain.DIFFICULT
    assert path_cost(grid, [(0, 0), (1, 0), (2, 0)]) == 15
    area = reachable(grid, (0, 0), 30)
    assert area[(6, 0)] == 30 and (7, 0) not in area
    occ = Occupancy(hostile=frozenset({(1, 1)}), friendly=frozenset({(0, 1)}))
    area = reachable(grid, (0, 0), 30, occ)
    assert (1, 1) not in area and (0, 1) not in area and (0, 2) in area
    with pytest.raises(RuleViolation):
        path_cost(grid, [(0, 0), (1, 1)], occ)
    with pytest.raises(RuleViolation):
        path_cost(grid, [(0, 0), (2, 0)])


def test_puertas_bloquean_hasta_abrirse() -> None:
    grid = room()
    assert shortest_path(grid, (0, 3), (9, 3)) is None
    grid.doors[(5, 3)] = DoorState.OPEN
    path = shortest_path(grid, (0, 3), (9, 3))
    assert path is not None and (5, 3) in path


def test_linea_de_vision_y_niebla() -> None:
    grid = room()
    lights = light_map(grid, [], Light.BRIGHT)
    seen = visible_cells(grid, Viewer((1, 3)), lights)
    assert (4, 0) in seen and (7, 3) not in seen
    assert not has_line_of_sight(grid, (1, 3), (8, 3))
    fog = Fog()
    fog.update(seen)
    grid.doors[(5, 3)] = DoorState.OPEN
    fog.update(visible_cells(grid, Viewer((1, 3)), lights))
    assert fog.state((8, 3)) == "visible"
    fog.update({(1, 3)})
    assert fog.state((8, 3)) == "explored"
    assert fog.state((9, 0)) in {"explored", "unknown"}


def test_oscuridad_y_vision_en_la_oscuridad() -> None:
    grid = Grid(20, 3)
    lights = light_map(grid, [LightSource((0, 1), 20, 20)], Light.DARK)
    assert lights[(3, 1)] is Light.BRIGHT and lights[(6, 1)] is Light.DIM and lights[(10, 1)] is Light.DARK
    human = visible_cells(grid, Viewer((0, 1)), lights)
    dwarf = visible_cells(grid, Viewer((0, 1), darkvision_ft=60), lights)
    assert (10, 1) not in human and (10, 1) in dwarf and (14, 1) not in dwarf
    assert visible_cells(grid, Viewer((0, 1), blinded=True), lights) == {(0, 1)}
