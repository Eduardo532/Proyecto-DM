"""Traducción de errores del dominio a respuestas HTTP con mensajes en español."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.engines.errors import RuleViolation
from app.services.errors import Conflict, Forbidden, NotFound


def install(app: FastAPI) -> None:
    def handler(status: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
        async def respond(_request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse({"detail": str(exc)}, status_code=status)

        return respond

    app.add_exception_handler(RuleViolation, handler(422))
    app.add_exception_handler(NotFound, handler(404))
    app.add_exception_handler(Conflict, handler(409))
    app.add_exception_handler(Forbidden, handler(403))

    async def integrity(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse({"detail": "La operación entra en conflicto con datos existentes."}, status_code=409)

    app.add_exception_handler(IntegrityError, integrity)
