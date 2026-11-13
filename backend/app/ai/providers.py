"""Proveedores de modelos de lenguaje intercambiables (D-05, D-10).

El resto del sistema solo usa la interfaz ``LLMProvider``. Para cambiar de modelo o de servicio
basta con la configuración (``VDM_LLM_*``).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any, Protocol

import httpx

from app.config import Settings

log = logging.getLogger("vdm.ai")

Message = dict[str, str]


class LLMUnavailable(RuntimeError):
    """No se pudo contactar con el modelo (Ollama apagado, modelo no descargado...)."""


class LLMProvider(Protocol):
    name: str

    def chat(self, messages: list[Message], *, schema: dict[str, Any] | None = None, aux: bool = False) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def status(self) -> dict[str, Any]: ...


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base = settings.llm_base_url.rstrip("/")

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(f"{self.base}{path}", json=body, timeout=self.settings.llm_timeout_seconds)
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"No se pudo conectar con Ollama en {self.base}: {exc}") from exc
        if response.status_code == 404:
            raise LLMUnavailable(f"Ollama no tiene el modelo solicitado: {response.text[:200]}")
        if response.status_code >= 400:
            raise LLMUnavailable(f"Ollama respondió {response.status_code}: {response.text[:200]}")
        data: dict[str, Any] = response.json()
        return data

    def chat(self, messages: list[Message], *, schema: dict[str, Any] | None = None, aux: bool = False) -> str:
        model = (self.settings.llm_aux_model or self.settings.llm_model) if aux else self.settings.llm_model
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": self.settings.llm_think,
            "options": {
                "temperature": 0.2 if schema else self.settings.llm_temperature,
                "num_ctx": int(self.settings.llm_context_budget * 1.6),
                # Los modelos pequeños tienden a copiar frases de la historia reciente.
                "repeat_penalty": 1.0 if schema else 1.15,
            },
        }
        if schema is not None:
            body["format"] = schema
        data = self._post("/api/chat", body)
        return str(data.get("message", {}).get("content", "")).strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        data = self._post("/api/embed", {"model": self.settings.embedding_model, "input": texts})
        vectors: list[list[float]] = data.get("embeddings", [])
        return vectors

    def status(self) -> dict[str, Any]:
        try:
            response = httpx.get(f"{self.base}/api/tags", timeout=5)
            names = [m.get("name", "") for m in response.json().get("models", [])]
        except (httpx.HTTPError, ValueError):
            return {"provider": self.name, "reachable": False, "models": [], "ready": False}
        wanted = {self.settings.llm_model, self.settings.embedding_model}
        missing = [w for w in wanted if not any(n == w or n == f"{w}:latest" for n in names)]
        return {"provider": self.name, "reachable": True, "models": names, "missing": missing, "ready": not missing,
                "model": self.settings.llm_model}


class OpenAICompatibleProvider:
    """Cualquier servidor con la API de OpenAI (LM Studio, llama.cpp, servicios externos)."""

    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base = settings.llm_base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}

    def chat(self, messages: list[Message], *, schema: dict[str, Any] | None = None, aux: bool = False) -> str:
        model = (self.settings.llm_aux_model or self.settings.llm_model) if aux else self.settings.llm_model
        body: dict[str, Any] = {"model": model, "messages": messages, "temperature": self.settings.llm_temperature}
        if schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "respuesta", "schema": schema}}
        try:
            response = httpx.post(f"{self.base}/chat/completions", json=body, headers=self.headers,
                                  timeout=self.settings.llm_timeout_seconds)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailable(str(exc)) from exc
        return str(response.json()["choices"][0]["message"]["content"]).strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = httpx.post(f"{self.base}/embeddings", json={"model": self.settings.embedding_model,
                                  "input": texts}, headers=self.headers, timeout=self.settings.llm_timeout_seconds)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailable(str(exc)) from exc
        return [item["embedding"] for item in response.json()["data"]]

    def status(self) -> dict[str, Any]:
        try:
            response = httpx.get(f"{self.base}/models", headers=self.headers, timeout=5)
            names = [m.get("id", "") for m in response.json().get("data", [])]
            return {"provider": self.name, "reachable": True, "models": names, "ready": True,
                    "model": self.settings.llm_model}
        except (httpx.HTTPError, ValueError):
            return {"provider": self.name, "reachable": False, "models": [], "ready": False}


class DisabledProvider:
    name = "none"

    def chat(self, messages: list[Message], *, schema: dict[str, Any] | None = None, aux: bool = False) -> str:
        raise LLMUnavailable("La IA está desactivada (VDM_LLM_PROVIDER=none).")

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise LLMUnavailable("La IA está desactivada.")

    def status(self) -> dict[str, Any]:
        return {"provider": self.name, "reachable": False, "models": [], "ready": False}


class ScriptedProvider:
    """Proveedor de pruebas: responde con una función que recibe los mensajes."""

    name = "scripted"

    def __init__(self, responder: Callable[[list[Message], dict[str, Any] | None], str],
                 embedder: Callable[[list[str]], list[list[float]]] | None = None) -> None:
        self.responder = responder
        self.embedder = embedder
        self.calls: list[tuple[list[Message], dict[str, Any] | None]] = []

    def chat(self, messages: list[Message], *, schema: dict[str, Any] | None = None, aux: bool = False) -> str:
        self.calls.append((messages, schema))
        return self.responder(messages, schema)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.embedder is None:
            raise LLMUnavailable("sin embeddings")
        return self.embedder(texts)

    def status(self) -> dict[str, Any]:
        return {"provider": self.name, "reachable": True, "models": [], "ready": True}


def build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings)
    if settings.llm_provider == "openai":
        return OpenAICompatibleProvider(settings)
    return DisabledProvider()


def parse_json(text: str) -> dict[str, Any]:
    """Extrae el primer objeto JSON de la respuesta (tolera texto alrededor)."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("La respuesta no contiene JSON.")
    data: dict[str, Any] = json.loads(text[start : end + 1])
    return data
