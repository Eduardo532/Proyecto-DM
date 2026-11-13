from pathlib import Path

from fastapi.testclient import TestClient

from tests.adventure import make_adventure_pdf
from tests.helpers import setup_table


def test_importacion_y_busqueda_filtrada(client: TestClient, tmp_path: Path) -> None:
    t = setup_table(client)
    cid, dm = t["cid"], t["dm"]
    pdf = make_adventure_pdf(tmp_path / "aventura.pdf").read_bytes()
    assert client.post(f"/api/campaigns/{cid}/documents", files={"file": ("a.pdf", pdf, "application/pdf")}).status_code == 403
    uploaded = client.post(f"/api/campaigns/{cid}/documents", files={"file": ("aventura.pdf", pdf, "application/pdf")},
                           headers=dm).json()
    assert uploaded["status"] == "ready", uploaded["log"]
    again = client.post(f"/api/campaigns/{cid}/documents", files={"file": ("copia.pdf", pdf, "application/pdf")},
                        headers=dm).json()
    assert again["id"] == uploaded["id"]  # mismo SHA-256: no se duplica

    chunks = client.get(f"/api/campaigns/{cid}/chunks", headers=dm).json()
    by_level = {c["knowledge_level"] for c in chunks}
    assert {"public", "conditional", "dm"} <= by_level
    read_aloud = next(c for c in chunks if c["kind"] == "read_aloud")
    assert "escalera" in read_aloud["text"] and read_aloud["knowledge_level"] == "public"
    assert any(c["kind"] == "stat_block" and c["knowledge_level"] == "dm" for c in chunks)

    scenes = client.get(f"/api/campaigns/{cid}/scenes", headers=dm).json()
    entrance = next(s for s in scenes if s["name"].startswith("1."))
    assert "escalera" in entrance["summary_public"]

    facts = client.get(f"/api/campaigns/{cid}/facts", headers=dm).json()
    door = next(f for f in facts if "puerta secreta" in f["statement"])
    assert door["discovery"] == {"skill": "perception", "dc": 15} and door["knowledge_level"] == "conditional"

    public_hits = client.get(f"/api/campaigns/{cid}/search", params={"q": "escalera oscuridad"}).json()
    assert public_hits and all(h["knowledge_level"] == "public" for h in public_hits)
    assert "p. 1" in public_hits[0]["citation"]
    assert client.get(f"/api/campaigns/{cid}/search", params={"q": "puerta secreta"}).json() == []
    assert client.get(f"/api/campaigns/{cid}/search", params={"q": "Varis villano"}).json() == []
    dm_hits = client.get(f"/api/campaigns/{cid}/search", params={"q": "puerta secreta"}, headers=dm).json()
    assert dm_hits and dm_hits[0]["knowledge_level"] == "conditional"

    chunk_id = next(c["id"] for c in chunks if "Varis" in c["text"])
    client.patch(f"/api/campaigns/{cid}/chunks/{chunk_id}", json={"knowledge_level": "public"}, headers=dm)
    assert client.get(f"/api/campaigns/{cid}/search", params={"q": "Varis"}).json()


def test_formato_no_admitido(client: TestClient) -> None:
    t = setup_table(client)
    response = client.post(f"/api/campaigns/{t['cid']}/documents", files={"file": ("x.txt", b"hola", "text/plain")},
                           headers=t["dm"])
    assert response.status_code == 422
