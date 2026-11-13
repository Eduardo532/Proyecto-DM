"""Voz del DM: convierte la narración en audio con un servidor local de texto a voz.

Se usa la API de OpenAI ``/v1/audio/speech`` (la implementan Kokoro-FastAPI y otros). El audio se guarda en
caché por texto y voz, así que repetir una narración no vuelve a generarlo.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings

SPANISH_PREFIXES = ("e",)  # Kokoro: ef_* / em_* son voces en español


class VoiceUnavailable(RuntimeError):
    pass


def clean_for_speech(text: str) -> str:
    """Quita marcas que no se leen en voz alta (asteriscos, almohadillas, guiones de lista)."""
    text = re.sub(r"[*_#`>]+", " ", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", text).strip()


def _cache_path(settings: Settings, text: str, voice: str, speed: float) -> Path:
    key = hashlib.sha256(f"{settings.tts_model}|{voice}|{speed:.2f}|{text}".encode()).hexdigest()[:32]
    return settings.data_dir / "voz" / f"{key}.mp3"


def synthesize(settings: Settings, text: str, voice: str | None = None, speed: float = 1.0) -> Path:
    if not settings.tts_url:
        raise VoiceUnavailable("No hay servidor de voz configurado (VDM_TTS_URL).")
    spoken = clean_for_speech(text)
    if not spoken:
        raise VoiceUnavailable("No hay texto que leer.")
    chosen = voice or settings.tts_voice
    target = _cache_path(settings, spoken, chosen, speed)
    if target.is_file():
        return target
    body: dict[str, Any] = {"model": settings.tts_model, "input": spoken, "voice": chosen,
                            "response_format": "mp3", "speed": speed}
    if chosen[:1] in SPANISH_PREFIXES:
        body["lang_code"] = "e"
    try:
        response = httpx.post(f"{settings.tts_url.rstrip('/')}/v1/audio/speech", json=body,
                              timeout=settings.tts_timeout_seconds)
    except httpx.HTTPError as exc:
        raise VoiceUnavailable(f"El servidor de voz no responde ({exc.__class__.__name__}).") from exc
    if response.status_code != 200 or not response.content:
        raise VoiceUnavailable(f"El servidor de voz respondió {response.status_code}.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    return target


def status(settings: Settings) -> dict[str, Any]:
    """Si hay servidor de voz y qué voces en español ofrece."""
    if not settings.tts_url:
        return {"available": False, "voices": [], "default": settings.tts_voice,
                "message": "Sin servidor de voz: se usa la voz del navegador."}
    try:
        response = httpx.get(f"{settings.tts_url.rstrip('/')}/v1/audio/voices", timeout=5)
        data = response.json() if response.status_code == 200 else {}
    except (httpx.HTTPError, ValueError):
        return {"available": False, "voices": [], "default": settings.tts_voice,
                "message": "El servidor de voz todavía no está listo (la primera vez descarga el modelo)."}
    voices = data.get("voices", []) if isinstance(data, dict) else []
    names = [v if isinstance(v, str) else str(v.get("name") or v.get("id") or "") for v in voices]
    spanish = sorted(n for n in names if n[:1] in SPANISH_PREFIXES and "_" in n)
    return {"available": True, "voices": spanish or names[:20], "default": settings.tts_voice, "message": ""}
