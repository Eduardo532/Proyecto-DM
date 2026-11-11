"""Punto de entrada del backend.

Arranque en desarrollo (desde ``backend/``)::

    uvicorn app.main:create_app --factory --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.ai.runtime import runtime
from app.api import campaigns, characters, combat, health, play, world, ws
from app.api.errors import install as install_error_handlers
from app.config import Settings, get_settings
from app.db import Database
from app.migrations import upgrade_to_head


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved.data_dir.mkdir(parents=True, exist_ok=True)
        if resolved.auto_migrate:
            upgrade_to_head(resolved.resolved_database_url)
        db = Database(resolved.resolved_database_url)
        app.state.db = db
        runtime.configure(db, resolved)
        try:
            yield
        finally:
            db.dispose()

    app = FastAPI(title=resolved.app_name, version=__version__, lifespan=lifespan)
    app.state.settings = resolved
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    for module in (health, campaigns, characters, play, world, combat):
        app.include_router(module.router, prefix="/api")
    app.include_router(ws.router)
    return app
