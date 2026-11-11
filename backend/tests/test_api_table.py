from fastapi.testclient import TestClient

from tests.helpers import setup_table


def test_campania_jugadores_y_ficha_con_valores_derivados(client: TestClient) -> None:
    t = setup_table(client)
    character = t["character"]
    assert character["hp_current"] == 28
    derived = character["derived"]
    assert derived["proficiency_bonus"] == 2
    assert derived["skills"]["athletics"] == 5
    assert derived["saves"]["con"] == 4
    assert derived["passive_perception"] == 13
    assert derived["attacks"][0] == {"name": "Hacha de batalla", "bonus": 5, "damage": "1d8+3", "damage_type": "slashing"}
    campaigns = client.get("/api/campaigns").json()
    assert campaigns[0]["has_dm_pin"] is True


def test_ficha_invalida_se_rechaza(client: TestClient) -> None:
    t = setup_table(client)
    bad = {"name": "X", "hp_max": 10, "sheet": {"abilities": {"str": 10}}}
    assert client.post(f"/api/campaigns/{t['cid']}/characters", json=bad).status_code == 422


def test_pin_del_dm(client: TestClient) -> None:
    t = setup_table(client)
    assert client.post(f"/api/campaigns/{t['cid']}/dm/login", json={"pin": "0000"}).status_code == 403
    assert client.get(f"/api/campaigns/{t['cid']}/facts", headers={"X-DM-Token": "falso"}).status_code == 200
    assert client.post(f"/api/campaigns/{t['cid']}/facts", json={"statement": "x"}).status_code == 403


def test_danio_y_historial(client: TestClient) -> None:
    t = setup_table(client)
    url = f"/api/campaigns/{t['cid']}/characters/{t['character']['id']}"
    hurt = client.post(f"{url}/hp", json={"kind": "damage", "amount": 30, "damage_type": "fire"}).json()
    assert hurt["hp_current"] == 0 and "unconscious" in hurt["conditions"]
    history = client.get(f"{url}/history").json()
    assert {h["field"] for h in history} >= {"hp_current", "conditions"}
    saved = client.post(f"{url}/death-save", params={"natural": 20}).json()
    assert saved["regained_consciousness"]
    assert client.get(url).json()["hp_current"] == 1


def test_edicion_con_version(client: TestClient) -> None:
    t = setup_table(client)
    url = f"/api/campaigns/{t['cid']}/characters/{t['character']['id']}"
    ok = client.patch(url, json={"level": 4, "version": t["character"]["version"]})
    assert ok.status_code == 200 and ok.json()["derived"]["proficiency_bonus"] == 2
    stale = client.patch(url, json={"level": 5, "version": t["character"]["version"]})
    assert stale.status_code == 409


def test_tirada_pedida_por_el_dm_con_cd_oculta(client: TestClient) -> None:
    t = setup_table(client)
    cid = t["cid"]
    session = client.post(f"/api/campaigns/{cid}/sessions").json()
    assert session["number"] == 1
    body = {"character_id": t["character"]["id"], "kind": "skill", "skill": "athletics", "difficulty": "media"}
    roll = client.post(f"/api/campaigns/{cid}/rolls", json=body, headers=t["dm"]).json()
    assert roll["dc"] is None and roll["status"] == "pending"
    assert client.get(f"/api/campaigns/{cid}/sessions/current").json()["state"] == "awaiting_roll"
    blocked = client.post(f"/api/campaigns/{cid}/actions", json={"character_id": t["character"]["id"], "text": "Corro"})
    assert blocked.status_code == 409
    bad = client.post(f"/api/campaigns/{cid}/rolls/{roll['id']}/resolve", json={"mode": "manual", "values": [25]})
    assert bad.status_code == 422
    done = client.post(f"/api/campaigns/{cid}/rolls/{roll['id']}/resolve", json={"mode": "manual", "values": [10]}).json()
    assert done["total"] == 15 and done["outcome"] == "success" and done["dc"] is None
    assert "d20 (10)" in done["breakdown"]
    again = client.post(f"/api/campaigns/{cid}/rolls/{roll['id']}/resolve", json={"mode": "digital"})
    assert again.status_code == 409
    public = client.get(f"/api/campaigns/{cid}/events").json()
    assert all(e["visibility"] == "public" for e in public)
    assert "roll_dc" not in {e["type"] for e in public}
    dm_events = client.get(f"/api/campaigns/{cid}/events", headers=t["dm"]).json()
    assert "roll_dc" in {e["type"] for e in dm_events}


def test_accion_libre_y_cierre_de_sesion(client: TestClient) -> None:
    t = setup_table(client)
    cid = t["cid"]
    assert client.post(f"/api/campaigns/{cid}/actions", json={"character_id": t["character"]["id"],
                       "text": "x"}).status_code == 409  # fmt: skip
    session = client.post(f"/api/campaigns/{cid}/sessions").json()
    client.patch(f"/api/campaigns/{cid}/sessions/{session['id']}", json={"active_player_id": t["player"]["id"]})
    action = client.post(f"/api/campaigns/{cid}/actions", json={"character_id": t["character"]["id"],
                         "text": "Examino el altar"})  # fmt: skip
    assert action.status_code == 202
    closed = client.post(f"/api/campaigns/{cid}/sessions/{session['id']}/close", json={}).json()
    assert closed["state"] == "closed"
    assert "Thorin: Examino el altar" in closed["summary"]["acontecimientos"]
    second = client.post(f"/api/campaigns/{cid}/sessions").json()
    assert second["number"] == 2 and second["active_player_id"] == t["player"]["id"]


def test_tirada_libre(client: TestClient) -> None:
    t = setup_table(client)
    result = client.post(f"/api/campaigns/{t['cid']}/rolls/free", json={"expression": "2d6+3", "mode": "manual",
                         "values": [4, 5]}).json()  # fmt: skip
    assert result["total"] == 12
    assert client.post(f"/api/campaigns/{t['cid']}/rolls/free", json={"expression": "2d7"}).status_code == 422
