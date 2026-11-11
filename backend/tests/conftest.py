from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # _env_file=None: las pruebas no leen el backend/.env del desarrollador.
    return Settings(_env_file=None, environment="test", data_dir=tmp_path / "data")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    # El bloque "with" ejecuta el arranque (migraciones) y el cierre de la aplicación.
    with TestClient(create_app(settings)) as test_client:
        yield test_client
