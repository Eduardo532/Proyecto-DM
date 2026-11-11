"""Personajes jugadores: fichas, valores derivados y cambios validados."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CampaignDep, Db, commit
from app.models import Campaign, Character, CharacterChange, Entity
from app.schemas.character import (
    CharacterChangeOut,
    CharacterCreate,
    CharacterOut,
    CharacterUpdate,
    ConditionChange,
    HpChange,
)
from app.services import characters as service
from app.services.errors import Conflict, NotFound
from app.services.events import append_event
from app.services.sessions import open_session

router = APIRouter(tags=["personajes"])


def character_out(character: Character) -> CharacterOut:
    out = CharacterOut.model_validate(character)
    out.derived = service.derived(character)
    return out


def get_character(db: Db, campaign: Campaign, character_id: str) -> Character:
    character = db.get(Character, character_id)
    if character is None or character.campaign_id != campaign.id:
        raise NotFound("El personaje no existe.")
    return character


@router.get("/campaigns/{campaign_id}/characters", response_model=list[CharacterOut])
def list_characters(campaign: CampaignDep, db: Db) -> list[CharacterOut]:
    rows = db.scalars(select(Character).where(Character.campaign_id == campaign.id).order_by(Character.created_at))
    return [character_out(c) for c in rows]


@router.post("/campaigns/{campaign_id}/characters", response_model=CharacterOut, status_code=201)
def create_character(campaign: CampaignDep, body: CharacterCreate, db: Db) -> CharacterOut:
    data = body.model_dump(exclude={"sheet", "hp_current"})
    character = Character(
        campaign_id=campaign.id,
        **data,
        hp_current=body.hp_max if body.hp_current is None else min(body.hp_current, body.hp_max),
        sheet=body.sheet.model_dump(),
        conditions=[],
        death_saves={"successes": 0, "failures": 0},
    )
    db.add(character)
    db.flush()
    service.to_engine(character)  # valida la ficha con el motor
    # Token en el mapa para poder posicionarlo más adelante.
    db.add(Entity(campaign_id=campaign.id, kind="character", character_id=character.id, name=character.name,
                  disposition="ally", token_color="#4f6b3a"))  # fmt: skip
    append_event(db, campaign.id, "character_created", {"character_id": character.id, "name": character.name})
    commit(db)
    return character_out(character)


@router.get("/campaigns/{campaign_id}/characters/{character_id}", response_model=CharacterOut)
def read_character(campaign: CampaignDep, character_id: str, db: Db) -> CharacterOut:
    return character_out(get_character(db, campaign, character_id))


@router.patch("/campaigns/{campaign_id}/characters/{character_id}", response_model=CharacterOut)
def update_character(campaign: CampaignDep, character_id: str, body: CharacterUpdate, db: Db) -> CharacterOut:
    character = get_character(db, campaign, character_id)
    if body.version != character.version:
        raise Conflict("La ficha cambió mientras la editabas. Recarga y vuelve a intentarlo.")
    changes = body.model_dump(exclude_unset=True, exclude={"version"})
    for key, value in changes.items():
        if key == "sheet" and body.sheet is not None:
            character.sheet = body.sheet.model_dump()
        elif value is not None or key == "player_id":
            setattr(character, key, value)
    character.hp_current = min(character.hp_current, character.hp_max)
    service.to_engine(character)
    character.version += 1
    entity = db.scalar(select(Entity).where(Entity.character_id == character.id))
    if entity:
        entity.name = character.name
    append_event(db, campaign.id, "character_edited", {"character_id": character.id, "fields": sorted(changes)})
    commit(db)
    return character_out(character)


@router.delete("/campaigns/{campaign_id}/characters/{character_id}", status_code=204)
def delete_character(campaign: CampaignDep, character_id: str, db: Db) -> None:
    db.delete(get_character(db, campaign, character_id))
    commit(db)


@router.post("/campaigns/{campaign_id}/characters/{character_id}/hp", response_model=CharacterOut)
def change_hp(campaign: CampaignDep, character_id: str, body: HpChange, db: Db) -> CharacterOut:
    character = get_character(db, campaign, character_id)
    session = open_session(db, campaign.id)
    service.change_hp(db, character, body.kind, body.amount, damage_type=body.damage_type, critical=body.critical,
                      reason=body.reason, session_id=session.id if session else None, actor_kind="player")  # fmt: skip
    commit(db)
    return character_out(character)


@router.post("/campaigns/{campaign_id}/characters/{character_id}/conditions", response_model=CharacterOut)
def change_condition(campaign: CampaignDep, character_id: str, body: ConditionChange, db: Db) -> CharacterOut:
    character = get_character(db, campaign, character_id)
    session = open_session(db, campaign.id)
    service.set_condition(db, character, body.condition, body.present, session_id=session.id if session else None,
                          actor_kind="player")  # fmt: skip
    commit(db)
    return character_out(character)


@router.post("/campaigns/{campaign_id}/characters/{character_id}/death-save", response_model=dict[str, Any])
def death_save(campaign: CampaignDep, character_id: str, natural: int, db: Db) -> dict[str, Any]:
    character = get_character(db, campaign, character_id)
    session = open_session(db, campaign.id)
    result = service.death_save(db, character, natural, session_id=session.id if session else None)
    commit(db)
    return result


@router.get("/campaigns/{campaign_id}/characters/{character_id}/history", response_model=list[CharacterChangeOut])
def history(campaign: CampaignDep, character_id: str, db: Db) -> list[CharacterChange]:
    get_character(db, campaign, character_id)
    return list(
        db.scalars(
            select(CharacterChange)
            .where(CharacterChange.character_id == character_id)
            .order_by(CharacterChange.created_at.desc())
            .limit(200)
        )
    )
