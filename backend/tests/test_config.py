from pathlib import Path

import pytest

from app.config import Settings


def test_database_url_por_defecto_esta_en_data_dir(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path)
    assert settings.resolved_database_url == f"sqlite:///{(tmp_path / 'vdm.sqlite3').as_posix()}"


def test_variables_de_entorno_con_prefijo_vdm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VDM_DATABASE_URL", "sqlite:///otra.sqlite3")
    monkeypatch.setenv("VDM_AUTO_MIGRATE", "false")
    settings = Settings(_env_file=None)
    assert settings.resolved_database_url == "sqlite:///otra.sqlite3"
    assert settings.auto_migrate is False
