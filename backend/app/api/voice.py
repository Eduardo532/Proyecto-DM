"""Voz del DM: estado del servidor de voz y audio de una narración."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.engines.errors import RuleViolation
from app.services import voice

router = APIRouter(tags=["voz"])


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str | None = Field(default=None, max_length=40, pattern=r"^[A-Za-z0-9_\-+.]+$")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


@router.get("/voice/status", response_model=dict[str, Any])
def voice_status(request: Request) -> dict[str, Any]:
    return voice.status(request.app.state.settings)


@router.post("/voice/speech")
def speech(body: SpeechRequest, request: Request) -> FileResponse:
    try:
        path = voice.synthesize(request.app.state.settings, body.text, body.voice, round(body.speed, 2))
    except voice.VoiceUnavailable as exc:
        raise RuleViolation(str(exc)) from exc
    return FileResponse(path, media_type="audio/mpeg")
