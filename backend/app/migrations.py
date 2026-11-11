"""Ejecución de migraciones de Alembic desde el código.

Se usa al arrancar el servidor (si ``auto_migrate`` está activo) y en las pruebas.
Desde la consola también se puede ejecutar ``alembic upgrade head`` dentro de ``backend/``.
"""

from alembic import command
from alembic.config import Config

from app.config import BACKEND_DIR


def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    # Evita que env.py reconfigure el logging de la aplicación.
    config.attributes["configure_logger"] = False
    return config


def upgrade_to_head(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")


def downgrade_to_base(database_url: str) -> None:
    command.downgrade(alembic_config(database_url), "base")
