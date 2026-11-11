"""Conexión a la base de datos.

En SQLite cada conexión nueva recibe estos ajustes (PRAGMA):

- ``foreign_keys=ON``: SQLite no comprueba las claves foráneas si no se activa.
- ``journal_mode=WAL``: permite leer mientras se escribe y es más resistente a cortes.
- ``synchronous=NORMAL``: equilibrio seguro entre velocidad y durabilidad con WAL.
- ``busy_timeout=5000``: espera hasta 5 s si otra conexión tiene el archivo bloqueado.
"""

from collections.abc import Iterator
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def _apply_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def create_db_engine(url: str) -> Engine:
    is_sqlite = url.startswith("sqlite")
    engine = create_engine(
        url,
        # FastAPI puede usar la conexión desde otro hilo; SQLAlchemy gestiona el acceso.
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )
    if is_sqlite:
        event.listen(engine, "connect", _apply_sqlite_pragmas)
    return engine


class Database:
    """Agrupa el motor de SQLAlchemy y la fábrica de sesiones."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.engine = create_db_engine(url)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def session(self) -> Iterator[Session]:
        with self.session_factory() as session:
            yield session

    def dispose(self) -> None:
        self.engine.dispose()
