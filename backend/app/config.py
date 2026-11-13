"""Configuración de la aplicación.

Los valores se leen, por orden de prioridad, de variables de entorno con el
prefijo ``VDM_`` y del archivo ``backend/.env``. Ejemplo: ``VDM_PORT=8001``.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VDM_",
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Virtual Dungeon Master"
    environment: Literal["development", "test", "production"] = "development"

    # Carpeta con la base de datos, los PDF, los mapas y las copias de seguridad.
    # Está fuera del control de versiones (ver .gitignore).
    data_dir: Path = REPO_DIR / "data"

    # Si no se indica, se usa data_dir/vdm.sqlite3.
    database_url: str | None = None

    # Aplicar migraciones pendientes al arrancar el servidor.
    auto_migrate: bool = True

    # Orígenes permitidos para el frontend en desarrollo (Vite usa el 5173).
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # --- IA (ver docs/guia-ollama.md) ---
    llm_provider: Literal["ollama", "openai", "none"] = "ollama"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""
    llm_model: str = "qwen3.5:2b"
    llm_aux_model: str = ""  # clasificación y resúmenes; vacío = el mismo modelo
    llm_context_budget: int = 5000  # tokens de entrada aproximados por llamada
    llm_timeout_seconds: float = 180.0
    llm_temperature: float = 0.7
    llm_think: bool = False  # razonamiento ("thinking"): más calidad, más lento
    embedding_model: str = "qwen3-embedding:0.6b"

    # --- Voz del DM (texto a voz). Vacío = sin servidor: la interfaz usa la voz del navegador. ---
    # Cualquier servidor con la API de OpenAI /v1/audio/speech; con Docker, Kokoro en el servicio «voz».
    tts_url: str = ""
    tts_voice: str = "em_alex"  # Kokoro en español: em_alex, em_santa (hombre), ef_dora (mujer)
    tts_model: str = "kokoro"
    tts_timeout_seconds: float = 60.0

    # Servir la interfaz compilada (frontend/dist) desde el backend.
    static_dir: Path | None = None

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        # as_posix() produce "C:/..." en Windows, que es lo que espera SQLAlchemy.
        return f"sqlite:///{(self.data_dir / 'vdm.sqlite3').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
