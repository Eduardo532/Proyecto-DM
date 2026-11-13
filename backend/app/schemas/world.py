from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import KnowledgeLevel, ORMModel


class SceneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    summary_public: str = ""
    summary_dm: str = ""
    map_id: str | None = None
    order_index: int = 0
    lighting: Literal["bright", "dim", "dark"] = "bright"


class SceneUpdate(BaseModel):
    name: str | None = None
    summary_public: str | None = None
    summary_dm: str | None = None
    map_id: str | None = None
    status: Literal["unvisited", "active", "visited"] | None = None
    order_index: int | None = None
    lighting: Literal["bright", "dim", "dark"] | None = None


class SceneOut(ORMModel):
    id: str
    name: str
    summary_public: str
    summary_dm: str
    map_id: str | None
    status: str
    order_index: int
    lighting: str


class MapCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    width_cells: int = Field(ge=1, le=200)
    height_cells: int = Field(ge=1, le=200)
    cell_size_ft: int = Field(default=5, ge=1, le=100)
    background_asset_id: str | None = None
    ambient_light: Literal["bright", "dim", "dark"] = "bright"
    fog_enabled: bool = True


class MapUpdate(BaseModel):
    name: str | None = None
    width_cells: int | None = Field(default=None, ge=1, le=200)
    height_cells: int | None = Field(default=None, ge=1, le=200)
    grid_offset_x: float | None = None
    grid_offset_y: float | None = None
    cell_size_px: float | None = Field(default=None, gt=2)
    # Enviar null explícitamente vuelve a casillas cuadradas.
    cell_height_px: float | None = Field(default=None, gt=2)
    ambient_light: Literal["bright", "dim", "dark"] | None = None
    fog_enabled: bool | None = None
    logic: dict[str, Any] | None = None
    reset_fog: bool = False


class EntityCreate(BaseModel):
    kind: Literal["npc", "creature", "object"]
    name: str = Field(min_length=1, max_length=120)
    name_public: str = ""
    scene_id: str | None = None
    map_id: str | None = None
    npc_id: str | None = None
    x: int | None = None
    y: int | None = None
    size: str = "medium"
    hp_max: int | None = Field(default=None, ge=1)
    armor_class: int | None = None
    hidden: bool = False
    disposition: Literal["ally", "neutral", "hostile"] = "neutral"
    stats: dict[str, Any] = {}
    token_color: str = "#8b1e1e"


class EntityUpdate(BaseModel):
    name: str | None = None
    name_public: str | None = None
    scene_id: str | None = None
    map_id: str | None = None
    hp_current: int | None = None
    hp_max: int | None = None
    armor_class: int | None = None
    conditions: list[str] | None = None
    hidden: bool | None = None
    disposition: Literal["ally", "neutral", "hostile"] | None = None
    stats: dict[str, Any] | None = None
    token_color: str | None = None
    x: int | None = None
    y: int | None = None


class Move(BaseModel):
    x: int
    y: int


class FactCreate(BaseModel):
    statement: str = Field(min_length=1)
    subject: str = ""
    scene_id: str | None = None
    knowledge_level: KnowledgeLevel = "dm"
    discovery: dict[str, Any] = {}
    keywords: list[str] = []
    status: Literal["true", "false_rumor", "hypothesis"] = "true"


class FactUpdate(BaseModel):
    statement: str | None = None
    subject: str | None = None
    scene_id: str | None = None
    knowledge_level: KnowledgeLevel | None = None
    discovery: dict[str, Any] | None = None
    keywords: list[str] | None = None
    status: Literal["true", "false_rumor", "hypothesis"] | None = None


class FactOut(ORMModel):
    id: str
    subject: str
    statement: str
    scene_id: str | None
    knowledge_level: str
    discovery: dict[str, Any]
    keywords: list[str]
    source: str
    status: str


class Reveal(BaseModel):
    to: Literal["party", "character"] = "party"
    character_id: str | None = None


class NpcIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    public_description: str = ""
    personality: str = ""
    motivations: str = ""
    secrets: str = ""
    voice: str = ""
    attitude: Literal["hostile", "indifferent", "friendly"] = "indifferent"
    status: Literal["alive", "dead", "missing"] = "alive"
    known_to_party: bool = False
    stats: dict[str, Any] = {}


class NpcOut(NpcIn, ORMModel):
    id: str


class QuestIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description_public: str = ""
    description_dm: str = ""
    status: Literal["unknown", "offered", "active", "completed", "failed"] = "unknown"


class QuestOut(QuestIn, ORMModel):
    id: str


class MemoryIn(BaseModel):
    scope: Literal["campaign", "character", "npc", "quest", "location", "session"] = "campaign"
    scope_id: str | None = None
    content: str = Field(min_length=1)
    importance: int = Field(default=3, ge=1, le=5)
    visibility: Literal["public", "dm"] = "public"


class MemoryOut(MemoryIn, ORMModel):
    id: str
    edited_by_dm: bool
    superseded_by: str | None
