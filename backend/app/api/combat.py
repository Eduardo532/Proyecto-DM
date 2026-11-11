"""Combate táctico: inicio, turnos, acciones y fin."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CampaignDep, Db, DmCampaign, IsDm, commit
from app.api.play import require_open_session
from app.services import combat as service

router = APIRouter(tags=["combate"])


class CombatStart(BaseModel):
    entity_ids: list[str]
    initiatives: dict[str, int] | None = None


class CombatAction(BaseModel):
    entity_id: str
    kind: Literal["action", "bonus", "reaction"] = "action"
    action: str = ""


@router.get("/campaigns/{campaign_id}/combat", response_model=dict[str, Any] | None)
def current(campaign: CampaignDep, db: Db, dm: IsDm) -> dict[str, Any] | None:
    combat = service.active_combat(db, campaign.id)
    return service.combat_view(db, combat, dm) if combat else None


@router.post("/campaigns/{campaign_id}/combat", response_model=dict[str, Any], status_code=201)
def start(campaign: DmCampaign, body: CombatStart, db: Db) -> dict[str, Any]:
    session = require_open_session(db, campaign)
    combat = service.start_combat(db, session, body.entity_ids, actor_kind="dm", initiatives=body.initiatives)
    commit(db)
    return service.combat_view(db, combat, dm=True)


@router.post("/campaigns/{campaign_id}/combat/next", response_model=dict[str, Any])
def next_turn(campaign: CampaignDep, db: Db, dm: IsDm) -> dict[str, Any]:
    combat = service.next_turn(db, campaign.id)
    commit(db)
    from app.ai.turn import schedule_enemy_turn

    schedule_enemy_turn(campaign.id)
    return service.combat_view(db, combat, dm)


@router.post("/campaigns/{campaign_id}/combat/action", response_model=dict[str, Any])
def spend(campaign: CampaignDep, body: CombatAction, db: Db, dm: IsDm) -> dict[str, Any]:
    combat = service.spend_action(db, campaign.id, body.entity_id, body.kind, body.action)
    commit(db)
    return service.combat_view(db, combat, dm)


@router.post("/campaigns/{campaign_id}/combat/end", response_model=dict[str, Any])
def end(campaign: DmCampaign, db: Db) -> dict[str, Any]:
    combat = service.end_combat(db, campaign.id)
    commit(db)
    return service.combat_view(db, combat, dm=True)
