"""Entorno de Alembic.

``render_as_batch=True`` permite modificar columnas en SQLite: Alembic recrea la
tabla copiando los datos, porque SQLite no admite ALTER TABLE completo.
"""

from logging.config import fileConfig

from alembic import context

from app.config import get_settings
from app.db import create_db_engine
from app.models import Base

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_name(name: str | None, type_: str, _parent: object) -> bool:
    """Las tablas de búsqueda FTS5 se gestionan a mano en las migraciones."""
    return not (type_ == "table" and name is not None and name.startswith("chunk_fts"))


def _database_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    return url or get_settings().resolved_database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_db_engine(_database_url())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                include_name=include_name,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
