"""Endpoint de salud: confirma que el servidor y la base de datos responden."""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError

from app import __version__
from app.db import Database

router = APIRouter(tags=["sistema"])


class DatabaseHealth(BaseModel):
    journal_mode: str
    foreign_keys: bool
    schema_revision: str | None


class HealthResponse(BaseModel):
    status: str
    version: str
    database: DatabaseHealth


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    db: Database = request.app.state.db
    with db.engine.connect() as conn:
        journal_mode = str(conn.exec_driver_sql("PRAGMA journal_mode").scalar_one())
        foreign_keys = bool(conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one())
        try:
            revision = conn.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one_or_none()
        except OperationalError:
            # La tabla no existe: la base de datos no se ha migrado todavía.
            revision = None
    return HealthResponse(
        status="ok",
        version=__version__,
        database=DatabaseHealth(
            journal_mode=journal_mode,
            foreign_keys=foreign_keys,
            schema_revision=revision,
        ),
    )
