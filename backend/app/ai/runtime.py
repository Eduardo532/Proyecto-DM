"""Estado compartido de la capa de IA (base de datos, configuración y trabajos en segundo plano)."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from app.ai.providers import DisabledProvider, LLMProvider, build_provider
from app.config import Settings
from app.db import Database

log = logging.getLogger("vdm.ai")


class Runtime:
    def __init__(self) -> None:
        self.database: Database | None = None
        self.settings: Settings | None = None
        # Un solo trabajador: los turnos de una mesa se procesan en orden.
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vdm-ai")
        self.synchronous = False  # en pruebas, ejecutar en el mismo hilo
        self.provider: LLMProvider = DisabledProvider()

    def configure(self, database: Database, settings: Settings, provider: LLMProvider | None = None) -> None:
        self.database = database
        self.settings = settings
        self.synchronous = settings.environment == "test"
        self.provider = provider or build_provider(settings)

    def submit(self, fn: Any, *args: Any) -> Future[Any] | None:
        if self.synchronous:
            fn(*args)
            return None
        future = self.executor.submit(fn, *args)
        future.add_done_callback(_log_errors)
        return future


def _log_errors(future: Future[Any]) -> None:
    exc = future.exception()
    if exc is not None:
        log.error("Error en un turno de IA", exc_info=exc)


runtime = Runtime()
