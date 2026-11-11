import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db import Database
from tests.helpers import setup_table


def _map_scene(client: TestClient, t: dict) -> tuple[str, str]:
    cid, dm = t["cid"], t["dm"]
    game_map = client.post(f"/api/campaigns/{cid}/maps", json={"name": "Cripta", "width_cells": 10, "height_cells": 6},
                           headers=dm).json()  # fmt: skip
    walls = [[5, y, "wall"] for y in range(6) if y != 3]
    logic = {"terrain": walls, "doors": [{"x": 5, "y": 3, "state": "closed"}], "lights": []}
    client.patch(f"/api/campaigns/{cid}/maps/{game_map['id']}", json={"logic": logic}, headers=dm)
    scene = client.post(f"/api/campaigns/{cid}/scenes", json={"name": "Osario", "summary_public": "Huesos.",
                        "summary_dm": "Hay un ghoul tras la puerta.", "map_id": game_map["id"]}, headers=dm).json()  # fmt: skip
    return game_map["id"], scene["id"]


def test_mapa_niebla_y_entidades_ocultas(client: TestClient) -> None:
    t = setup_table(client)
    cid, dm = t["cid"], t["dm"]
    map_id, scene_id = _map_scene(client, t)
    session = client.post(f"/api/campaigns/{cid}/sessions").json()
    client.patch(f"/api/campaigns/{cid}/sessions/{session['id']}", json={"scene_id": scene_id})
    token = next(e for e in client.get(f"/api/campaigns/{cid}/entities").json() if e["kind"] == "character")
    client.patch(f"/api/campaigns/{cid}/entities/{token['id']}", json={"map_id": map_id, "scene_id": scene_id})
    placed = client.post(f"/api/campaigns/{cid}/entities/{token['id']}/move", json={"x": 1, "y": 3})
    assert placed.status_code == 200
    ghoul = client.post(f"/api/campaigns/{cid}/entities", json={"kind": "creature", "name": "Ghoul",
                        "name_public": "Figura encorvada", "scene_id": scene_id, "map_id": map_id, "x": 8, "y": 3,
                        "hp_max": 22, "disposition": "hostile"}, headers=dm).json()  # fmt: skip
    hidden_rat = client.post(f"/api/campaigns/{cid}/entities", json={"kind": "creature", "name": "Rata",
                             "scene_id": scene_id, "map_id": map_id, "x": 2, "y": 1, "hidden": True}, headers=dm)  # fmt: skip
    assert hidden_rat.status_code == 201
    seen = {e["name"] for e in client.get(f"/api/campaigns/{cid}/entities", params={"scene_id": scene_id}).json()}
    assert seen == {"Thorin"}  # el ghoul está tras la puerta y la rata escondida
    player_map = client.get(f"/api/campaigns/{cid}/maps/{map_id}").json()
    assert [8, 3] not in player_map["explored"] and [2, 3] in player_map["visible"]
    assert all(t[0] <= 5 for t in player_map["logic"]["terrain"])
    blocked = client.post(f"/api/campaigns/{cid}/entities/{token['id']}/move", json={"x": 7, "y": 3})
    assert blocked.status_code == 422
    client.patch(f"/api/campaigns/{cid}/maps/{map_id}", json={"logic": {"terrain": [[5, y, "wall"] for y in range(6)
                 if y != 3], "doors": [{"x": 5, "y": 3, "state": "open"}], "lights": []}}, headers=dm)  # fmt: skip
    seen = client.get(f"/api/campaigns/{cid}/entities", params={"scene_id": scene_id}).json()
    ghoul_view = next(e for e in seen if e["id"] == ghoul["id"])
    assert ghoul_view["name"] == "Figura encorvada" and ghoul_view["health"] == "ileso" and "stats" not in ghoul_view
    scenes = client.get(f"/api/campaigns/{cid}/scenes").json()
    assert scenes[0]["summary"] == "Huesos." and "summary_dm" not in scenes[0]


def test_hechos_revelados_y_memoria(client: TestClient) -> None:
    t = setup_table(client)
    cid, dm = t["cid"], t["dm"]
    secret = client.post(f"/api/campaigns/{cid}/facts", json={"statement": "El altar tiene un resorte",
                         "knowledge_level": "conditional"}, headers=dm).json()  # fmt: skip
    client.post(f"/api/campaigns/{cid}/facts", json={"statement": "El sacerdote es el villano"}, headers=dm)
    assert client.get(f"/api/campaigns/{cid}/facts").json() == []
    client.post(f"/api/campaigns/{cid}/facts/{secret['id']}/reveal", json={"to": "party"}, headers=dm)
    known = client.get(f"/api/campaigns/{cid}/facts").json()
    assert [f["statement"] for f in known] == ["El altar tiene un resorte"]
    memory = client.post(f"/api/campaigns/{cid}/memory", json={"content": "Thorin mintió al guardia"}, headers=dm).json()
    fixed = client.put(f"/api/campaigns/{cid}/memory/{memory['id']}", json={"content": "Thorin engañó al guardia"},
                       headers=dm).json()  # fmt: skip
    listed = client.get(f"/api/campaigns/{cid}/memory").json()
    assert [m["id"] for m in listed] == [fixed["id"]]


def test_combate_por_turnos(client: TestClient) -> None:
    t = setup_table(client)
    cid, dm = t["cid"], t["dm"]
    map_id, scene_id = _map_scene(client, t)
    client.post(f"/api/campaigns/{cid}/sessions")
    token = next(e for e in client.get(f"/api/campaigns/{cid}/entities").json() if e["kind"] == "character")
    client.patch(f"/api/campaigns/{cid}/entities/{token['id']}", json={"map_id": map_id, "scene_id": scene_id})
    client.post(f"/api/campaigns/{cid}/entities/{token['id']}/move", json={"x": 0, "y": 0})
    goblin = client.post(f"/api/campaigns/{cid}/entities", json={"kind": "creature", "name": "Goblin",
                         "map_id": map_id, "scene_id": scene_id, "x": 3, "y": 0, "hp_max": 7, "disposition": "hostile",
                         "stats": {"dex": 14}}, headers=dm).json()  # fmt: skip
    combat = client.post(f"/api/campaigns/{cid}/combat", json={"entity_ids": [token["id"], goblin["id"]],
                         "initiatives": {token["id"]: 15, goblin["id"]: 10}}, headers=dm).json()  # fmt: skip
    assert combat["current_entity_id"] == token["id"]
    assert client.get(f"/api/campaigns/{cid}/sessions/current").json()["state"] == "combat"
    moved = client.post(f"/api/campaigns/{cid}/entities/{token['id']}/move", json={"x": 0, "y": 4})
    assert moved.status_code == 200 and moved.json()["cost_ft"] == 20
    too_far = client.post(f"/api/campaigns/{cid}/entities/{token['id']}/move", json={"x": 0, "y": 0})
    assert too_far.status_code == 422  # velocidad 25: quedan 5 pies
    client.post(f"/api/campaigns/{cid}/combat/action", json={"entity_id": token["id"], "kind": "action"})
    again = client.post(f"/api/campaigns/{cid}/combat/action", json={"entity_id": token["id"], "kind": "action"})
    assert again.status_code == 422
    after = client.post(f"/api/campaigns/{cid}/combat/next").json()
    assert after["current_entity_id"] == goblin["id"]
    ended = client.post(f"/api/campaigns/{cid}/combat/end", headers=dm).json()
    assert ended["status"] == "ended"


def test_eventos_inmutables_y_borrado_de_campania(client: TestClient) -> None:
    t = setup_table(client)
    database: Database = client.app.state.db  # type: ignore[attr-defined]
    with database.engine.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("UPDATE event SET type = 'x'"))
    with database.engine.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("DELETE FROM event"))
    assert client.delete(f"/api/campaigns/{t['cid']}").status_code == 403
    assert client.delete(f"/api/campaigns/{t['cid']}", headers=t["dm"]).status_code == 204
    with database.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM event")).scalar_one() == 0
