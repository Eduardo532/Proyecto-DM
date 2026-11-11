from typing import Any

from fastapi.testclient import TestClient

FIGHTER = {
    "name": "Thorin",
    "race": "Enano",
    "char_class": "Guerrero",
    "level": 3,
    "hp_max": 28,
    "armor_class": 18,
    "speed_ft": 25,
    "sheet": {
        "abilities": {"str": 16, "dex": 12, "con": 14, "int": 10, "wis": 13, "cha": 8},
        "skill_proficiencies": ["athletics", "perception"],
        "save_proficiencies": ["str", "con"],
        "darkvision_ft": 60,
        "attacks": [{"name": "Hacha de batalla", "ability": "str", "damage": "1d8", "damage_type": "slashing"}],
    },
}


def setup_table(client: TestClient, pin: str = "1234") -> dict[str, Any]:
    campaign = client.post("/api/campaigns", json={"name": "La Cripta", "dm_pin": pin, "dice_mode": "ask"}).json()
    cid = campaign["id"]
    player = client.post(f"/api/campaigns/{cid}/players", json={"display_name": "Eduardo"}).json()
    character = client.post(f"/api/campaigns/{cid}/characters", json={**FIGHTER, "player_id": player["id"]}).json()
    token = client.post(f"/api/campaigns/{cid}/dm/login", json={"pin": pin}).json()["token"]
    return {"cid": cid, "player": player, "character": character, "dm": {"X-DM-Token": token}}
