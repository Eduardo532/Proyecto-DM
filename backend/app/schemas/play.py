from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class SessionOut(ORMModel):
    id: str
    campaign_id: str
    number: int
    state: str
    scene_id: str | None
    active_player_id: str | None
    ai_paused: bool
    summary: dict[str, Any]
    started_at: datetime
    ended_at: datetime | None


class SessionUpdate(BaseModel):
    active_player_id: str | None = None
    scene_id: str | None = None
    ai_paused: bool | None = None


class SessionClose(BaseModel):
    summary: dict[str, Any] | None = None
    generate_summary: bool = True


class CheckRequest(BaseModel):
    character_id: str
    kind: Literal["ability", "skill", "save", "attack", "initiative"]
    skill: str | None = None
    ability: Literal["str", "dex", "con", "int", "wis", "cha"] | None = None
    dc: int | None = Field(default=None, ge=1, le=40)
    difficulty: Literal["muy_facil", "facil", "media", "dificil", "muy_dificil", "casi_imposible"] | None = None
    dc_public: bool = False
    advantage: Literal["none", "advantage", "disadvantage"] = "none"
    reason: str = ""


class RollResolve(BaseModel):
    mode: Literal["digital", "manual"]
    values: list[int] | None = None


class FreeRoll(BaseModel):
    expression: str = Field(min_length=1, max_length=100)
    mode: Literal["digital", "manual"] = "digital"
    values: list[int] | None = None
    label: str = ""
    character_id: str | None = None


class PlayerAction(BaseModel):
    character_id: str
    player_id: str | None = None
    text: str = Field(min_length=1, max_length=2000)
    target: str | None = None  # elemento del mapa seleccionado, p. ej. "door:3:4" o un id de entidad
