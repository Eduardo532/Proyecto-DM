from pathlib import Path

from sqlalchemy import inspect

from app.db import create_db_engine
from app.migrations import downgrade_to_base, upgrade_to_head


def _tablas(url: str) -> set[str]:
    engine = create_db_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_migraciones_suben_bajan_y_vuelven_a_subir(tmp_path: Path) -> None:
    url = f"sqlite:///{(tmp_path / 'migraciones.sqlite3').as_posix()}"

    upgrade_to_head(url)
    assert {"alembic_version", "app_setting", "campaign", "event", "chunk_fts"} <= _tablas(url)

    downgrade_to_base(url)
    assert "app_setting" not in _tablas(url) and "chunk_fts" not in _tablas(url)

    upgrade_to_head(url)
    assert "app_setting" in _tablas(url)


def test_modelos_y_migraciones_coinciden(tmp_path: Path) -> None:
    """Si alguien cambia un modelo sin crear la migración, esta prueba falla."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.models import Base

    url = f"sqlite:///{(tmp_path / 'comparacion.sqlite3').as_posix()}"
    upgrade_to_head(url)
    engine = create_db_engine(url)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(
                conn,
                opts={"include_name": lambda name, type_, _p: not (type_ == "table" and str(name).startswith("chunk_fts"))},
            )
            diferencias = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()
    assert diferencias == []
