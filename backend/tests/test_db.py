from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.db import Database


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(f"sqlite:///{(tmp_path / 'prueba.sqlite3').as_posix()}")
    yield database
    database.dispose()


def test_cada_conexion_activa_wal_y_claves_foraneas(db: Database) -> None:
    with db.engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert conn.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 5000


def test_sqlite_rechaza_claves_foraneas_invalidas(db: Database) -> None:
    with db.engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE padre (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql(
            "CREATE TABLE hijo (id INTEGER PRIMARY KEY, padre_id INTEGER NOT NULL "
            "REFERENCES padre(id))"
        )
    with pytest.raises(IntegrityError), db.engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO hijo (id, padre_id) VALUES (1, 999)")
