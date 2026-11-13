"""Importación universal: tipo y contenido detectado de cada archivo, variantes de mapa y casillas rectangulares

Solo se añaden columnas (ALTER TABLE ADD COLUMN): no hace falta recrear tablas con datos.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-13 12:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_COLUMNS: list[tuple[str, sa.Column[object]]] = [
    ("document", sa.Column("kind", sa.String(length=20), server_default="pdf", nullable=False)),
    ("document", sa.Column("manifest", sa.JSON(), server_default="[]", nullable=False)),
    ("document", sa.Column("parent_id", sa.String(length=32), nullable=True)),
    ("document_asset", sa.Column("original_name", sa.String(length=300), server_default="", nullable=False)),
    ("document_asset", sa.Column("group_key", sa.String(length=200), server_default="", nullable=False)),
    ("document_asset", sa.Column("variant", sa.String(length=20), server_default="", nullable=False)),
    ("document_asset", sa.Column("meta", sa.JSON(), server_default="{}", nullable=False)),
    ("map", sa.Column("cell_height_px", sa.Double(), nullable=True)),
    ("map", sa.Column("dm_background_asset_id", sa.String(length=32), nullable=True)),
]


def upgrade() -> None:
    for table, column in NEW_COLUMNS:
        op.add_column(table, column)


def downgrade() -> None:
    # SQLite >= 3.35 borra columnas sin recrear la tabla (así no se disparan las claves foráneas).
    for table, column in reversed(NEW_COLUMNS):
        op.execute(f'ALTER TABLE "{table}" DROP COLUMN "{column.name}"')
