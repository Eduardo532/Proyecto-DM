"""Punto de entrada del backend.

Arranque en desarrollo (desde ``backend/``)::

    uvicorn app.main:create_app --factory --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from pathlib import Path

from fastapi.responses import FileResponse

from app.ai.providers import LLMProvider
from app.ai.runtime import runtime
from app.api import campaigns, characters, combat, documents, health, play, world, ws
from app.api.errors import install as install_error_handlers
from app.config import Settings, get_settings
from app.db import Database
from app.migrations import upgrade_to_head


def create_app(settings: Settings | None = None, provider: LLMProvider | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved.data_dir.mkdir(parents=True, exist_ok=True)
        if resolved.auto_migrate:
            upgrade_to_head(resolved.resolved_database_url)
        db = Database(resolved.resolved_database_url)
        app.state.db = db
        runtime.configure(db, resolved, provider)
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
    for module in (health, campaigns, characters, play, world, combat, documents):
        app.include_router(module.router, prefix="/api")
    app.include_router(ws.router)
    if resolved.static_dir and (resolved.static_dir / "index.html").is_file():
        _serve_frontend(app, resolved.static_dir)
    return app


def _serve_frontend(app: FastAPI, static_dir: Path) -> None:
    """Sirve la interfaz compilada. Las rutas desconocidas devuelven index.html (aplicación de una página)."""
    root = static_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(root / "index.html")
