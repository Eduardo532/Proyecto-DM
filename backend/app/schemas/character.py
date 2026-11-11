from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.engines.rules.abilities import SKILLS, Ability
from app.schemas.common import ORMModel

ABILITY_KEYS = [a.value for a in Ability]


class Attack(BaseModel):
    name: str
    ability: Literal["str", "dex", "con", "int", "wis", "cha"] = "str"
    proficient: bool = True
    attack_bonus_extra: int = 0
    damage: str = "1d6"
    damage_type: str = "slashing"
    reach_ft: int = 5
    range_ft: int | None = None
    range_long_ft: int | None = None


class Spell(BaseModel):
    name: str
    level: int = Field(ge=0, le=9)
    prepared: bool = True
    description: str = ""


class SpellSlot(BaseModel):
    max: int = Field(ge=0, le=9)
    used: int = Field(default=0, ge=0)


class Feature(BaseModel):
    name: str
    description: str = ""
    uses_max: int | None = None
    uses_used: int = 0


class InventoryItem(BaseModel):
    name: str
    quantity: int = Field(default=1, ge=0)
    equipped: bool = False
    weight_lb: float = 0
    notes: str = ""


class Coins(BaseModel):
    cp: int = 0
    sp: int = 0
    ep: int = 0
    gp: int = 0
    pp: int = 0


class SheetData(BaseModel):
    """Contenido de la ficha guardado en la columna JSON ``character.sheet``."""

    abilities: dict[str, int] = Field(default_factory=lambda: dict.fromkeys(ABILITY_KEYS, 10))
    skill_proficiencies: list[str] = []
    skill_expertise: list[str] = []
    save_proficiencies: list[str] = []
    jack_of_all_trades: bool = False
    initiative_bonus_extra: int = 0
    darkvision_ft: int = 0
    resistances: list[str] = []
    immunities: list[str] = []
    vulnerabilities: list[str] = []
    attacks: list[Attack] = []
    spellcasting_ability: str | None = None
    spells: list[Spell] = []
    spell_slots: dict[str, SpellSlot] = {}
    features: list[Feature] = []
    feats: list[str] = []
    inventory: list[InventoryItem] = []
    coins: Coins = Coins()
    languages: list[str] = []
    other_proficiencies: list[str] = []
    hit_die: str = "d8"
    hit_dice_used: int = 0
    personality: str = ""

    @field_validator("abilities")
    @classmethod
    def _abilities(cls, value: dict[str, int]) -> dict[str, int]:
        if set(value) != set(ABILITY_KEYS):
            raise ValueError("Deben indicarse las seis características.")
        for key, score in value.items():
            if not 1 <= score <= 30:
                raise ValueError(f"{key}: la puntuación debe estar entre 1 y 30.")
        return value

    @field_validator("skill_proficiencies", "skill_expertise")
    @classmethod
    def _skills(cls, value: list[str]) -> list[str]:
        unknown = [s for s in value if s not in SKILLS]
        if unknown:
            raise ValueError(f"Habilidades desconocidas: {', '.join(unknown)}.")
        return sorted(set(value))

    @field_validator("save_proficiencies")
    @classmethod
    def _saves(cls, value: list[str]) -> list[str]:
        if any(v not in ABILITY_KEYS for v in value):
            raise ValueError("Salvaciones no válidas.")
        return sorted(set(value))


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    player_id: str | None = None
    race: str = ""
    char_class: str = ""
    subclass: str = ""
    level: int = Field(default=1, ge=1, le=20)
    background: str = ""
    alignment: str = ""
    xp: int = Field(default=0, ge=0)
    hp_max: int = Field(ge=1, le=999)
    hp_current: int | None = None
    armor_class: int = Field(default=10, ge=1, le=40)
    speed_ft: int = Field(default=30, ge=0, le=200)
    sheet: SheetData = SheetData()
    notes: str = ""


class CharacterUpdate(BaseModel):
    """Edición directa de la ficha (fuera de juego o por el DM). No cambia PG actuales."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    player_id: str | None = None
    race: str | None = None
    char_class: str | None = None
    subclass: str | None = None
    level: int | None = Field(default=None, ge=1, le=20)
    background: str | None = None
    alignment: str | None = None
    xp: int | None = Field(default=None, ge=0)
    hp_max: int | None = Field(default=None, ge=1, le=999)
    armor_class: int | None = Field(default=None, ge=1, le=40)
    speed_ft: int | None = Field(default=None, ge=0, le=200)
    sheet: SheetData | None = None
    notes: str | None = None
    version: int


class Derived(BaseModel):
    proficiency_bonus: int
    ability_modifiers: dict[str, int]
    skills: dict[str, int]
    saves: dict[str, int]
    initiative: int
    passive_perception: int
    passive_investigation: int
    passive_insight: int
    spell_save_dc: int | None
    spell_attack_bonus: int | None
    attacks: list[dict[str, str | int]]


class CharacterOut(ORMModel):
    id: str
    campaign_id: str
    player_id: str | None
    name: str
    race: str
    char_class: str
    subclass: str
    level: int
    background: str
    alignment: str
    xp: int
    sheet: SheetData
    hp_max: int
    hp_current: int
    hp_temp: int
    armor_class: int
    speed_ft: int
    conditions: list[str]
    exhaustion: int
    death_saves: dict[str, int]
    stable: bool
    status: str
    notes: str
    version: int
    derived: Derived | None = None


class HpChange(BaseModel):
    kind: Literal["damage", "heal", "temp"]
    amount: int = Field(ge=0, le=999)
    damage_type: str = ""
    critical: bool = False
    reason: str = ""


class ConditionChange(BaseModel):
    condition: str
    present: bool


class CharacterChangeOut(ORMModel):
    id: str
    field: str
    before: object
    after: object
    reason: str
