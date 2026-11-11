from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

KnowledgeLevel = Literal["public", "conditional", "dm"]
DiceMode = Literal["digital", "manual", "ask"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Timestamps(ORMModel):
    created_at: datetime
    updated_at: datetime
