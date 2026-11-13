"""Fichas y reconocimiento de archivos con documentos sintéticos."""

from pathlib import Path

from app.importing.detect import detect_file
from app.importing.sheets.reader import read_sheet
from app.schemas.character import CharacterCreate
from tests.importing.images import battle_map, illustration, round_icon
from tests.importing.pdfs import ddb_sheet, spanish_text_sheet


def test_ficha_de_formulario_tipo_dndbeyond(tmp_path: Path) -> None:
    sheet = read_sheet(ddb_sheet(tmp_path / "kira.pdf"))
    assert sheet.format == "dndbeyond" and sheet.confidence() >= 0.6
    assert (sheet.name, sheet.char_class, sheet.level) == ("Kira Vientoalto", "Rogue", 3)
    assert sheet.abilities == {"str": 8, "dex": 17, "con": 14, "int": 12, "wis": 13, "cha": 10}
    skills, expertise, saves, _ = sheet.derive_proficiencies()
    assert {"stealth", "acrobatics", "perception"} <= set(skills) and expertise == ["stealth"]
    assert saves == ["dex", "int"]
    assert (sheet.hp_max, sheet.armor_class, sheet.speed_ft, sheet.darkvision_ft) == (20, 15, 25, 60)
    assert [a["ability"] for a in sheet.attacks] == ["dex", "dex"]
    assert any(f["name"].startswith("Sneak Attack") for f in sheet.features)
    assert sheet.languages == ["Common", "Halfling"]
    character = CharacterCreate.model_validate(sheet.to_character())
    assert character.sheet.hit_die == "d8" and character.notes == "Jugador original: Ana"


def test_ficha_plana_en_espanol(tmp_path: Path) -> None:
    sheet = read_sheet(spanish_text_sheet(tmp_path / "lia.pdf"))
    assert sheet.format == "hoja_es"
    assert (sheet.name, sheet.char_class, sheet.level, sheet.race) == ("Lía Brasa", "Mago", 2, "Elfa")
    assert sheet.abilities == {"str": 8, "dex": 14, "con": 13, "int": 16, "wis": 12, "cha": 10}
    assert (sheet.hp_max, sheet.armor_class, sheet.speed_ft, sheet.darkvision_ft) == (14, 12, 30, 60)
    assert set(sheet.derive_proficiencies()[0]) == {"arcana", "history"}
    assert sheet.languages == ["Común", "Élfico", "Dracónico"]
    CharacterCreate.model_validate(sheet.to_character())


def test_reconoce_cada_tipo_de_archivo(tmp_path: Path) -> None:
    assert detect_file(ddb_sheet(tmp_path / "k.pdf"), "Personajes/k.pdf").kind == "character"
    grid = battle_map(tmp_path / "campo.png")
    assert detect_file(grid, "Fotos/campo.png").kind == "map"  # por la cuadrícula
    plain = battle_map(tmp_path / "sin.png", cell=None)
    found = detect_file(plain, "Maps/Cripta Map DM Version.png")
    assert (found.kind, found.variant, found.group_key) == ("map", "dm", "cripta map")
    assert detect_file(illustration(tmp_path / "retrato.png"), "Images/retrato.png").kind == "handout"
    icon = round_icon(tmp_path / "icono.png")
    marker = detect_file(icon, "Set/V1/3_Prone.png")
    assert marker.kind == "marker" and marker.meta["condition"] == "prone" and marker.name == "Prone"
    assert detect_file(icon, "Set/V1/11_Feared.png").meta["condition"] == "frightened"
    assert detect_file(icon, "Tokens/Goblin.png").kind == "token"
    assert detect_file(tmp_path / "notas.txt", "notas.txt").kind == "ignored"
