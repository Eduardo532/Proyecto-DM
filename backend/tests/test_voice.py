from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import voice


def test_sin_servidor_de_voz(client: TestClient) -> None:
    assert client.get("/api/voice/status").json()["available"] is False
    assert client.post("/api/voice/speech", json={"text": "Hola"}).status_code == 422


def test_audio_con_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, json: dict[str, Any], timeout: float) -> httpx.Response:
        calls.append({"url": url, **json})
        return httpx.Response(200, content=b"ID3-audio")

    monkeypatch.setattr(voice.httpx, "post", fake_post)
    settings = Settings(_env_file=None, environment="test", data_dir=tmp_path / "data", llm_provider="none",
                        tts_url="http://voz:8880")
    with TestClient(create_app(settings)) as client:
        text = "**La puerta** cruje.\n- Huele a humedad."
        first = client.post("/api/voice/speech", json={"text": text, "speed": 1.1})
        assert first.status_code == 200 and first.headers["content-type"] == "audio/mpeg"
        assert first.content == b"ID3-audio"
        assert client.post("/api/voice/speech", json={"text": text, "speed": 1.1}).content == b"ID3-audio"
    assert len(calls) == 1  # la segunda vez sale de la caché
    assert calls[0]["url"] == "http://voz:8880/v1/audio/speech"
    assert calls[0]["input"] == "La puerta cruje. Huele a humedad."
    assert calls[0]["voice"] == "em_alex" and calls[0]["lang_code"] == "e" and calls[0]["speed"] == 1.1


def test_voz_no_valida(client: TestClient) -> None:
    assert client.post("/api/voice/speech", json={"text": "Hola", "voice": "../etc"}).status_code == 422
