"""Importación universal por la API: un ZIP con aventura, fichas, mapas con variantes, ilustraciones y marcadores."""

import io
import zipfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from tests.adventure import make_adventure_pdf
from tests.helpers import setup_table
from tests.importing.images import battle_map, illustration, round_icon
from tests.importing.pdfs import ddb_sheet


def _bundle(tmp_path: Path) -> bytes:
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as nested:
        nested.write(battle_map(tmp_path / "sotano.png", cell=(50, 50), seed=5), "Sotano Map.png")
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as bundle:
        bundle.write(make_adventure_pdf(tmp_path / "cripta.pdf"), "Cripta/La_Cripta.pdf")
        bundle.write(ddb_sheet(tmp_path / "kira.pdf"), "Personajes/Kira.pdf")
        bundle.write(battle_map(tmp_path / "p.png", cell=None, seed=2), "Cripta/Maps/Cripta Map Player Version.png")
        bundle.write(battle_map(tmp_path / "d.png", cell=None, seed=3), "Cripta/Maps/Cripta Map DM Version.png")
        bundle.write(battle_map(tmp_path / "g.png", cell=(40, 30), seed=4), "Cripta/Maps/Batalla with Grid.png")
        bundle.write(battle_map(tmp_path / "n.png", cell=None, seed=4), "Cripta/Maps/Batalla no Grid.png")
        bundle.write(illustration(tmp_path / "r.png"), "Cripta/Images/Retrato del villano.png")
        bundle.write(round_icon(tmp_path / "m1.png"), "Marcadores/V1/3_Prone.png")
        bundle.write(round_icon(tmp_path / "m2.png"), "Marcadores/V1/11_Feared.png")
        bundle.write(round_icon(tmp_path / "m3.png"), "Marcadores/V2/3_Prone.png")
        bundle.write(round_icon(tmp_path / "t.png", color=(40, 120, 40)), "Tokens/Goblin.png")
        bundle.writestr("Credits.txt", "Gracias")
        bundle.writestr("__MACOSX/._Credits.txt", "basura")
        bundle.writestr("extras/sotano.zip", inner.getvalue())
    return data.getvalue()


def _by_name(manifest: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(item for item in manifest if item["name"] == name)


def test_importa_un_zip_completo(client: TestClient, tmp_path: Path) -> None:
    t = setup_table(client)
    cid, dm = t["cid"], t["dm"]
    response = client.post(f"/api/campaigns/{cid}/documents", headers=dm,
                           files={"file": ("pack.zip", _bundle(tmp_path), "application/zip")})
    assert response.status_code == 202, response.text
    pack = response.json()
    assert pack["status"] == "ready" and pack["kind"] == "archive", pack["log"]
    manifest = pack["manifest"]
    kinds = {item["path"]: item["kind"] for item in manifest}
    assert kinds["Cripta/La_Cripta.pdf"] == "adventure"
    assert kinds["Personajes/Kira.pdf"] == "character"
    assert kinds["Cripta/Images/Retrato del villano.png"] == "handout"
    assert kinds["Tokens/Goblin.png"] == "token"
    assert kinds["Credits.txt"] == "ignored"
    assert kinds["extras/sotano.zip/Sotano Map.png"] == "map"
    assert not any("__MACOSX" in path for path in kinds)

    # La aventura se procesa como cualquier PDF y queda enlazada al ZIP.
    documents = client.get(f"/api/campaigns/{cid}/documents", headers=dm).json()
    adventure = next(d for d in documents if d["parent_id"] == pack["id"])
    assert adventure["status"] == "ready" and adventure["kind"] == "pdf"
    assert any(s["name"].startswith("1.") for s in client.get(f"/api/campaigns/{cid}/scenes", headers=dm).json())

    # Mapas: variantes agrupadas, cuadrícula rectangular medida y versión limpia para la mesa.
    maps = {m["name"]: m for m in client.get(f"/api/campaigns/{cid}/maps", headers=dm).json()}
    assert set(maps) == {"Cripta Map", "Batalla", "Sotano Map"}
    battle = maps["Batalla"]
    assert (battle["cell_size_px"], battle["cell_height_px"]) == (40.0, 30.0)
    assert (battle["width_cells"], battle["height_cells"]) == (20, 20)
    assert maps["Sotano Map"]["cell_size_px"] == 50.0 and maps["Sotano Map"]["cell_height_px"] is None
    crypt = maps["Cripta Map"]
    assert crypt["has_background"] and crypt["has_dm_background"]
    player_image = client.get(f"/api/campaigns/{cid}/maps/{crypt['id']}/image").content
    assert client.get(f"/api/campaigns/{cid}/maps/{crypt['id']}/image", params={"variant": "dm"}).status_code == 403
    dm_image = client.get(f"/api/campaigns/{cid}/maps/{crypt['id']}/image", params={"variant": "dm"}, headers=dm)
    assert dm_image.status_code == 200 and dm_image.content != player_image
    assert _by_name(manifest, "Batalla no Grid")["status"] == "done"

    # Marcadores: uno por estado (la versión repetida se ignora) y visibles para la mesa.
    markers = client.get(f"/api/campaigns/{cid}/markers").json()
    assert sorted(m["condition"] for m in markers) == ["frightened", "prone"]
    assert client.get(f"/api/campaigns/{cid}/assets/{markers[0]['asset_id']}/image").status_code == 200
    portrait = _by_name(manifest, "Retrato del villano")
    assert client.get(f"/api/campaigns/{cid}/assets/{portrait['ref_id']}/image").status_code == 403

    # La ficha queda como borrador hasta que el DM la confirma.
    index = next(i for i, item in enumerate(manifest) if item["kind"] == "character")
    assert manifest[index]["status"] == "draft" and manifest[index]["draft"]["name"] == "Kira Vientoalto"
    names = [c["name"] for c in client.get(f"/api/campaigns/{cid}/characters").json()]
    assert "Kira Vientoalto" not in names
    url = f"/api/campaigns/{cid}/documents/{pack['id']}/items/{index}/confirm"
    assert client.post(url, json={}).status_code == 403
    confirmed = client.post(url, json={"overrides": {"name": "Kira"}}, headers=dm)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["manifest"][index]["status"] == "done"
    kira = next(c for c in client.get(f"/api/campaigns/{cid}/characters").json() if c["name"] == "Kira")
    assert kira["sheet"]["abilities"]["dex"] == 17 and "stealth" in kira["sheet"]["skill_expertise"]
    assert client.post(url, json={}, headers=dm).status_code == 422  # no se crea dos veces


def test_importa_archivos_sueltos(client: TestClient, tmp_path: Path) -> None:
    t = setup_table(client)
    cid, dm = t["cid"], t["dm"]
    sheet = client.post(f"/api/campaigns/{cid}/documents", headers=dm,
                        files={"file": ("kira.pdf", ddb_sheet(tmp_path / "k.pdf").read_bytes(), "application/pdf")})
    body = sheet.json()
    assert body["kind"] == "sheet" and body["manifest"][0]["status"] == "draft", body["log"]

    image = battle_map(tmp_path / "x.png", cell=(64, 64), width=1280, height=896).read_bytes()
    uploaded = client.post(f"/api/campaigns/{cid}/documents", headers=dm,
                           files={"file": ("Torre Battlemap.png", image, "image/png")}).json()
    assert uploaded["kind"] == "image" and uploaded["manifest"][0]["kind"] == "map"
    game_map = next(m for m in client.get(f"/api/campaigns/{cid}/maps", headers=dm).json() if m["name"] == "Torre Battlemap")
    assert (game_map["width_cells"], game_map["height_cells"], game_map["cell_size_px"]) == (20, 14, 64.0)

    # Se puede volver a medir la cuadrícula después de cambiarla a mano.
    client.patch(f"/api/campaigns/{cid}/maps/{game_map['id']}", json={"cell_size_px": 30, "cell_height_px": 45},
                 headers=dm)
    again = client.post(f"/api/campaigns/{cid}/maps/{game_map['id']}/detect-grid", headers=dm).json()
    assert again["cell_size_px"] == 64.0 and again["cell_height_px"] is None and again["grid_confidence"] > 0.45

    response = client.post(f"/api/campaigns/{cid}/documents", headers=dm, files={"file": ("x.docx", b"x", "a/b")})
    assert response.status_code == 422
