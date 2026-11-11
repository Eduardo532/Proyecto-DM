from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import DiceMode, ORMModel, Timestamps


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    dice_mode: DiceMode = "ask"
    dm_pin: str | None = Field(default=None, min_length=4, max_length=32)


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    dice_mode: DiceMode | None = None
    settings: dict[str, Any] | None = None
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class CampaignOut(Timestamps):
    id: str
    name: str
    description: str
    game_system: str
    dice_mode: str
    settings: dict[str, Any]
    status: str
    has_dm_pin: bool = False


class PlayerCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#b8913a", max_length=20)
    turn_order: int | None = None


class PlayerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = None
    turn_order: int | None = None


class PlayerOut(ORMModel):
    id: str
    campaign_id: str
    display_name: str
    color: str
    turn_order: int


class DmLogin(BaseModel):
    pin: str = ""


class DmToken(BaseModel):
    token: str
    expires_in_seconds: int
