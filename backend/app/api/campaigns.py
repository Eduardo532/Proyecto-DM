"""Campañas, participantes y acceso al modo DM."""

from __future__ import annotations

from fastapi import APIRouter, Header
from sqlalchemy import func, select

from app.api.deps import CampaignDep, Db, commit
from app.models import Campaign, Player
from app.schemas.campaign import (
    CampaignCreate,
    CampaignOut,
    CampaignUpdate,
    DmLogin,
    DmToken,
    PlayerCreate,
    PlayerOut,
    PlayerUpdate,
)
from app.services.dm_auth import TOKEN_TTL_SECONDS, hash_pin, tokens, verify_pin
from app.services.errors import Forbidden, NotFound
from app.services.events import append_event

router = APIRouter(tags=["campañas"])


def campaign_out(campaign: Campaign) -> CampaignOut:
    out = CampaignOut.model_validate(campaign)
    out.has_dm_pin = campaign.dm_pin_hash is not None
    return out


@router.get("/campaigns", response_model=list[CampaignOut])
def list_campaigns(db: Db, include_archived: bool = False) -> list[CampaignOut]:
    query = select(Campaign).order_by(Campaign.updated_at.desc())
    if not include_archived:
        query = query.where(Campaign.status == "active")
    return [campaign_out(c) for c in db.scalars(query)]


@router.post("/campaigns", response_model=CampaignOut, status_code=201)
def create_campaign(body: CampaignCreate, db: Db) -> CampaignOut:
    campaign = Campaign(
        name=body.name.strip(),
        description=body.description,
        dice_mode=body.dice_mode,
        dm_pin_hash=hash_pin(body.dm_pin) if body.dm_pin else None,
        settings={"vision": "group", "language": "es"},
    )
    db.add(campaign)
    db.flush()
    append_event(db, campaign.id, "campaign_created", {"name": campaign.name})
    commit(db)
    return campaign_out(campaign)


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign: CampaignDep) -> CampaignOut:
    return campaign_out(campaign)


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign: CampaignDep, body: CampaignUpdate, db: Db) -> CampaignOut:
    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "settings" and value is not None:
            campaign.settings = {**campaign.settings, **value}
        elif value is not None:
            setattr(campaign, key, value)
    commit(db)
    return campaign_out(campaign)


@router.delete("/campaigns/{campaign_id}", status_code=204)
def delete_campaign(campaign: CampaignDep, db: Db, x_dm_token: str | None = Header(default=None)) -> None:
    if campaign.dm_pin_hash and not tokens.check(x_dm_token, campaign.id):
        raise Forbidden("Para borrar una campaña con PIN hace falta el modo DM.")
    db.delete(campaign)
    commit(db)


# ------------------------------------------------------------------ DM ----
@router.post("/campaigns/{campaign_id}/dm/login", response_model=DmToken)
def dm_login(campaign: CampaignDep, body: DmLogin) -> DmToken:
    if not verify_pin(body.pin, campaign.dm_pin_hash):
        raise Forbidden("PIN incorrecto.")
    return DmToken(token=tokens.issue(campaign.id), expires_in_seconds=TOKEN_TTL_SECONDS)


@router.post("/campaigns/{campaign_id}/dm/logout", status_code=204)
def dm_logout(campaign: CampaignDep, x_dm_token: str | None = Header(default=None)) -> None:
    if x_dm_token:
        tokens.revoke(x_dm_token)


@router.put("/campaigns/{campaign_id}/dm/pin", status_code=204)
def dm_set_pin(campaign: CampaignDep, body: DmLogin, db: Db, x_dm_token: str | None = Header(default=None)) -> None:
    if campaign.dm_pin_hash and not tokens.check(x_dm_token, campaign.id):
        raise Forbidden("Hace falta el modo DM para cambiar el PIN.")
    campaign.dm_pin_hash = hash_pin(body.pin) if body.pin else None
    commit(db)


# ------------------------------------------------------------ jugadores ---
@router.get("/campaigns/{campaign_id}/players", response_model=list[PlayerOut])
def list_players(campaign: CampaignDep, db: Db) -> list[Player]:
    return list(db.scalars(select(Player).where(Player.campaign_id == campaign.id).order_by(Player.turn_order)))


@router.post("/campaigns/{campaign_id}/players", response_model=PlayerOut, status_code=201)
def create_player(campaign: CampaignDep, body: PlayerCreate, db: Db) -> Player:
    order = body.turn_order
    if order is None:
        order = (db.scalar(select(func.max(Player.turn_order)).where(Player.campaign_id == campaign.id)) or 0) + 1
    player = Player(campaign_id=campaign.id, display_name=body.display_name.strip(), color=body.color, turn_order=order)
    db.add(player)
    db.flush()
    append_event(db, campaign.id, "player_joined", {"player_id": player.id, "name": player.display_name})
    commit(db)
    return player


def _player(db: Db, campaign: Campaign, player_id: str) -> Player:
    player = db.get(Player, player_id)
    if player is None or player.campaign_id != campaign.id:
        raise NotFound("El participante no existe.")
    return player


@router.patch("/campaigns/{campaign_id}/players/{player_id}", response_model=PlayerOut)
def update_player(campaign: CampaignDep, player_id: str, body: PlayerUpdate, db: Db) -> Player:
    player = _player(db, campaign, player_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(player, key, value)
    commit(db)
    return player


@router.delete("/campaigns/{campaign_id}/players/{player_id}", status_code=204)
def delete_player(campaign: CampaignDep, player_id: str, db: Db) -> None:
    db.delete(_player(db, campaign, player_id))
    commit(db)
