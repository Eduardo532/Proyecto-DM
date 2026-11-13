"""Piezas puras del importador: texto, variantes de mapa, cuadrícula, orden de lectura y ZIP seguros."""

import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from app.document_processing.layout import reading_order
from app.importing.maps import cells_for, clean_stem, display_name, estimate_grid_array, variant_of
from app.importing.pdftext import split_icons, undouble, undouble_line
from app.importing.sheets.model import attack_from, estimate_slots, parse_class_level, parse_speed, ParsedSheet
from app.importing.zipwalk import extract_archive


def test_texto_duplicado_e_iconos() -> None:
    assert undouble("TTiieefflliinngg") == "Tiefling"
    assert undouble("yy") == "y" and undouble("Hola") == "Hola"
    assert undouble_line("TThhee OOffffeerriinngg RRoooomm") == "The Offering Room"
    assert undouble_line("Aaron see the moon") == "Aaron see the moon"
    words = split_icons("xxMedicina", 0, 0, 90, 10, 0)
    assert [w.text for w in words] == ["", "Medicina"]


def test_variantes_de_mapa() -> None:
    assert variant_of("Outpost Landing Map DM Version.png") == ("outpost landing map", "dm")
    assert variant_of("Outpost Landing Map Player Version.png") == ("outpost landing map", "player")
    assert variant_of("Stillfen Battlemap with Grid.png")[1] == "grid"
    assert variant_of("Stillfen Battlemap no Grid.png") == ("stillfen battlemap", "nogrid")
    assert variant_of("Stillfen Battlemap with Zones.png") == ("stillfen battlemap", "zones")
    assert variant_of("Mapa del jugador - Cripta.png") == ("cripta", "player")
    assert variant_of("Mapa del DM - Cripta.png") == ("cripta", "dm")
    assert clean_stem("446954-Player_Map_-_House_-_Floor_1.png") == "Player Map - House - Floor 1"
    assert display_name("446954-Player_Map_-_House_-_Floor_1.png") == "House - Floor 1"


def _grid_image(width: int, height: int, cell: tuple[int, int] | None, offset: tuple[int, int] = (0, 0)) -> np.ndarray:
    rng = np.random.default_rng(3)
    noise = rng.normal(140, 30, (height, width)).clip(0, 255).astype(np.uint8)
    image = np.asarray(Image.fromarray(noise).filter(ImageFilter.GaussianBlur(3)), dtype=np.float32).copy()
    if cell:
        image[:, offset[0]::cell[0]] = 20
        image[offset[1]::cell[1], :] = 20
    return image


def test_cuadricula_rectangular_y_desplazada() -> None:
    guess = estimate_grid_array(_grid_image(840, 590, (70, 59), (5, 10)))
    assert (guess.cell_w, guess.cell_h) == (70.0, 59.0)
    assert abs(guess.offset_x - 5) <= 1 and abs(guess.offset_y - 10) <= 1
    assert guess.confidence > 0.6 and not guess.square
    assert cells_for(840, 590, 70, 59) == (12, 10)


def test_cuadricula_cuadrada_y_sin_cuadricula() -> None:
    square = estimate_grid_array(_grid_image(900, 600, (50, 50)))
    assert square.square and square.cell_w == 50.0
    assert estimate_grid_array(_grid_image(900, 600, None)).confidence < 0.45


@dataclass
class _Box:
    name: str
    bbox: tuple[float, float, float, float]


def test_orden_de_lectura_a_dos_columnas() -> None:
    blocks = [
        _Box("titulo", (50, 40, 560, 60)),
        _Box("izq1", (50, 80, 290, 200)), _Box("der1", (320, 80, 560, 200)),
        _Box("izq2", (50, 210, 290, 400)), _Box("der2", (320, 210, 560, 400)),
        _Box("pie", (50, 420, 560, 440)),
    ]
    assert [b.name for b in reading_order(blocks, 612)] == ["titulo", "izq1", "izq2", "der1", "der2", "pie"]
    single = [_Box("a", (50, 80, 560, 100)), _Box("b", (50, 120, 560, 140))]
    assert [b.name for b in reading_order(single, 612)] == ["a", "b"]


def test_zip_seguro_y_anidado(tmp_path: Path) -> None:
    inner = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner, "w") as bundle:
        bundle.writestr("Mapas/Sotano Map.png", b"png")
    outer = tmp_path / "outer.zip"
    with zipfile.ZipFile(outer, "w") as bundle:
        bundle.writestr("../fuera.txt", b"no")
        bundle.writestr("__MACOSX/._basura", b"no")
        bundle.writestr("Aventura/modulo.pdf", b"%PDF")
        bundle.write(inner, "extras/inner.zip")
    files = extract_archive(outer, tmp_path / "out")
    assert sorted(f.relative for f in files) == ["Aventura/modulo.pdf", "extras/inner.zip/Mapas/Sotano Map.png"]
    assert not (tmp_path / "fuera.txt").exists()
    assert all(f.path.is_relative_to((tmp_path / "out").resolve()) for f in files)


def test_utilidades_de_ficha() -> None:
    assert parse_class_level("Paladín 3 / Brujo 2")[2] == 5
    assert parse_class_level("Cleric 3 (Life Domain)")[1] == "Life Domain"
    assert parse_speed("9 m") == 30 and parse_speed("25 ft.") == 25
    assert estimate_slots("Paladín", 3) == {"1": {"max": 3, "used": 0}}
    assert estimate_slots("Mago", 5)["3"] == {"max": 2, "used": 0}
    assert estimate_slots("Guerrero", 5) == {}
    sheet = ParsedSheet(format="texto", level=3, abilities={"str": 15, "dex": 10, "con": 14, "int": 10, "wis": 10,
                                                            "cha": 16})
    attack = attack_from("Mazo de guerra", 4, "2d6 +2 de daño contundente", sheet)
    assert attack["ability"] == "str" and attack["damage"].startswith("2d6") and attack["damage_type"] == "bludgeoning"
