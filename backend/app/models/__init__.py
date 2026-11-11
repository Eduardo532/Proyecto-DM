"""Modelos de base de datos.

Importar aquí cada modelo para que Alembic los encuentre en ``Base.metadata``.
"""

from app.models.app_setting import AppSetting
from app.models.base import Base
from app.models.campaign import Campaign, Character, CharacterChange, Npc, Player, Quest
from app.models.content import Document, DocumentAsset, DocumentChunk, Entity, Fact, FactAwareness, GameMap, Scene
from app.models.play import Combat, DiceRoll, Event, GameSession, MemoryEntry

__all__ = [
    "AppSetting",
    "Base",
    "Campaign",
    "Character",
    "CharacterChange",
    "Combat",
    "DiceRoll",
    "Document",
    "DocumentAsset",
    "DocumentChunk",
    "Entity",
    "Event",
    "Fact",
    "FactAwareness",
    "GameMap",
    "GameSession",
    "MemoryEntry",
    "Npc",
    "Player",
    "Quest",
    "Scene",
]
