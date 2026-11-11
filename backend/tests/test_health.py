from fastapi.testclient import TestClient

from app import __version__
from app.config import Settings


def test_health_confirma_servidor_y_base_de_datos(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": __version__,
        "database": {"journal_mode": "wal", "foreign_keys": True, "schema_revision": "0002"},
    }


def test_el_arranque_crea_la_carpeta_de_datos_y_la_base(
    client: TestClient, settings: Settings
) -> None:
    assert (settings.data_dir / "vdm.sqlite3").is_file()


def test_cors_permite_el_frontend_de_desarrollo(client: TestClient) -> None:
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
