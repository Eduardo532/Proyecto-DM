import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.ai.guard import leaks
from app.ai.providers import Message, ScriptedProvider
from app.config import Settings
from app.main import create_app
from app.models import Fact
from tests.helpers import setup_table


class Script:
    def __init__(self) -> None:
        self.decision: dict[str, Any] = {}
        self.narrations: list[str] = []
        self.default = "La luz de las antorchas tiembla sobre la piedra."

    def __call__(self, messages: list[Message], schema: dict[str, Any] | None) -> str:
        if schema and "tipo" in schema["properties"]:
            base = {"intencion": "", "tipo": "automatica", "prueba": "ninguna", "habilidad": "ninguna",
                    "caracteristica": "ninguna", "dificultad": "media", "ventaja": "none", "hecho": "ninguno",
                    "pnj": "ninguno", "motivo": "", "pregunta": ""}
            return json.dumps({**base, **self.decision})
        if schema:
            return json.dumps({"acontecimientos": ["El grupo exploró la cripta."], "decisiones": [],
                               "situacion_final": "Ante el altar.", "ganchos_abiertos": []})
        return self.narrations.pop(0) if self.narrations else self.default


@pytest.fixture
def script() -> Script:
    return Script()


@pytest.fixture
def ai_client(tmp_path: Path, script: Script) -> Iterator[TestClient]:
    settings = Settings(_env_file=None, environment="test", data_dir=tmp_path / "data", llm_provider="none")
    with TestClient(create_app(settings, provider=ScriptedProvider(script))) as client:
        yield client


def narrations(client: TestClient, cid: str) -> list[dict[str, Any]]:
    return [e["payload"] for e in client.get(f"/api/campaigns/{cid}/events").json() if e["type"] == "narration"]


def test_turno_con_tirada_y_revelacion(ai_client: TestClient, script: Script) -> None:
    t = setup_table(ai_client)
    cid, dm = t["cid"], t["dm"]
    scene = ai_client.post(f"/api/campaigns/{cid}/scenes", json={"name": "Capilla", "summary_public": "Un altar."},
                           headers=dm).json()
    fact = ai_client.post(f"/api/campaigns/{cid}/facts", json={"statement": "El altar esconde un resorte",
                          "scene_id": scene["id"], "knowledge_level": "conditional",
                          "discovery": {"skill": "investigation", "dc": 15}}, headers=dm).json()
    session = ai_client.post(f"/api/campaigns/{cid}/sessions").json()
    script.narrations = ["Entráis en una capilla fría."]
    ai_client.patch(f"/api/campaigns/{cid}/sessions/{session['id']}", json={"scene_id": scene["id"]})
    assert narrations(ai_client, cid)[-1] == {"text": "Entráis en una capilla fría.", "kind": "scene",
                                              "scene_id": scene["id"]}

    # El modelo propone Percepción y CD difícil, pero el hecho del PDF manda: Investigación CD 15.
    script.decision = {"tipo": "requiere_tirada", "prueba": "habilidad", "habilidad": "perception",
                       "dificultad": "dificil", "hecho": "H1", "intencion": "buscar un mecanismo"}
    action = {"character_id": t["character"]["id"], "text": "Busco mecanismos en el altar"}
    assert ai_client.post(f"/api/campaigns/{cid}/actions", json=action).status_code == 202
    pending = ai_client.get(f"/api/campaigns/{cid}/rolls", params={"status": "pending"}, headers=dm).json()
    assert len(pending) == 1 and pending[0]["skill"] == "investigation" and pending[0]["dc"] == 15
    assert narrations(ai_client, cid)[-1]["kind"] == "roll_prompt"

    script.narrations = ["Palpas la piedra sin encontrar nada útil."]
    ai_client.post(f"/api/campaigns/{cid}/rolls/{pending[0]['id']}/resolve", json={"mode": "manual", "values": [14]})
    assert ai_client.get(f"/api/campaigns/{cid}/facts").json() == []
    assert narrations(ai_client, cid)[-1]["text"] == "Palpas la piedra sin encontrar nada útil."

    ai_client.post(f"/api/campaigns/{cid}/actions", json=action)
    roll = ai_client.get(f"/api/campaigns/{cid}/rolls", params={"status": "pending"}).json()[0]
    assert roll["dc"] is None  # la mesa no ve la CD
    script.narrations = ["Un clic metálico: el altar cede."]
    ai_client.post(f"/api/campaigns/{cid}/rolls/{roll['id']}/resolve", json={"mode": "manual", "values": [19]})
    assert [f["id"] for f in ai_client.get(f"/api/campaigns/{cid}/facts").json()] == [fact["id"]]

    closed = ai_client.post(f"/api/campaigns/{cid}/sessions/{session['id']}/close", json={}).json()
    assert closed["summary"]["situacion_final"] == "Ante el altar."
    assert closed["summary"]["generado_por"] == "ia"


def test_aclaracion_y_accion_automatica(ai_client: TestClient, script: Script) -> None:
    t = setup_table(ai_client)
    cid = t["cid"]
    ai_client.post(f"/api/campaigns/{cid}/sessions")
    script.decision = {"tipo": "aclaracion", "pregunta": "¿Qué puerta quieres abrir?"}
    ai_client.post(f"/api/campaigns/{cid}/actions", json={"character_id": t["character"]["id"], "text": "Abro"})
    assert narrations(ai_client, cid)[-1]["text"] == "¿Qué puerta quieres abrir?"
    script.decision = {"tipo": "automatica"}
    script.narrations = ["Avanzas por el pasillo."]
    ai_client.post(f"/api/campaigns/{cid}/actions", json={"character_id": t["character"]["id"], "text": "Camino"})
    assert narrations(ai_client, cid)[-1]["text"] == "Avanzas por el pasillo."


def test_filtro_de_fugas(ai_client: TestClient, script: Script) -> None:
    t = setup_table(ai_client)
    cid, dm = t["cid"], t["dm"]
    ai_client.post(f"/api/campaigns/{cid}/facts", json={"statement": "El sacerdote Varis es el villano",
                   "keywords": ["Varis"]}, headers=dm)
    ai_client.post(f"/api/campaigns/{cid}/sessions")
    script.decision = {"tipo": "automatica"}
    script.narrations = ["Varis sonríe con malicia.", "El sacerdote sigue rezando."]
    ai_client.post(f"/api/campaigns/{cid}/actions", json={"character_id": t["character"]["id"], "text": "Observo"})
    assert narrations(ai_client, cid)[-1]["text"] == "El sacerdote sigue rezando."


def test_guardia_detecta_nombres_propios() -> None:
    fact = Fact(statement="Tras el altar espera Malek, el rey ceniza.", keywords=["corona negra"])
    assert leaks("Malek os observa.", [fact]) == ["malek"]
    assert leaks("Veis una CORONA NEGRA.", [fact]) == ["corona negra"]
    assert leaks("Un altar polvoriento.", [fact]) == []
