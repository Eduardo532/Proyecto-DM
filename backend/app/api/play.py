"""Sesiones, eventos, tiradas y acciones de la mesa."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.api.characters import get_character
from app.api.deps import CampaignDep, Db, DmCampaign, IsDm, commit
from app.engines.rules.checks import CheckKind
from app.models import Campaign, DiceRoll, Event, GameSession, Player, Scene
from app.schemas.play import CheckRequest, FreeRoll, PlayerAction, RollResolve, SessionClose, SessionOut, SessionUpdate
from app.services import rolls as roll_service
from app.services import sessions as session_service
from app.services.errors import Conflict, NotFound
from app.services.events import append_event, event_to_dict

router = APIRouter(tags=["mesa"])


def _session(db: Db, campaign: Campaign, session_id: str) -> GameSession:
    session = db.get(GameSession, session_id)
    if session is None or session.campaign_id != campaign.id:
        raise NotFound("La sesión no existe.")
    return session


def require_open_session(db: Db, campaign: Campaign) -> GameSession:
    session = session_service.open_session(db, campaign.id)
    if session is None:
        raise Conflict("No hay ninguna sesión abierta. Inicia una sesión primero.")
    return session


# ------------------------------------------------------------- sesiones ---
@router.get("/campaigns/{campaign_id}/sessions", response_model=list[SessionOut])
def list_sessions(campaign: CampaignDep, db: Db) -> list[GameSession]:
    query = select(GameSession).where(GameSession.campaign_id == campaign.id).order_by(GameSession.number.desc())
    return list(db.scalars(query))


@router.get("/campaigns/{campaign_id}/sessions/current", response_model=SessionOut | None)
def current_session(campaign: CampaignDep, db: Db) -> GameSession | None:
    return session_service.open_session(db, campaign.id)


@router.post("/campaigns/{campaign_id}/sessions", response_model=SessionOut, status_code=201)
def start_session(campaign: CampaignDep, db: Db) -> GameSession:
    session = session_service.start_session(db, campaign)
    commit(db)
    return session


@router.patch("/campaigns/{campaign_id}/sessions/{session_id}", response_model=SessionOut)
def update_session(campaign: CampaignDep, session_id: str, body: SessionUpdate, db: Db) -> GameSession:
    session = _session(db, campaign, session_id)
    fields = body.model_dump(exclude_unset=True)
    if "active_player_id" in fields:
        player = db.get(Player, body.active_player_id) if body.active_player_id else None
        if body.active_player_id and (player is None or player.campaign_id != campaign.id):
            raise NotFound("El participante no existe.")
        session.active_player_id = body.active_player_id
        append_event(db, campaign.id, "active_player", {"player_id": body.active_player_id,
                     "name": player.display_name if player else None}, session_id=session.id)
    if "scene_id" in fields:
        scene = db.get(Scene, body.scene_id) if body.scene_id else None
        if body.scene_id and (scene is None or scene.campaign_id != campaign.id):
            raise NotFound("La escena no existe.")
        session.scene_id = body.scene_id
        if scene:
            scene.status = "active"
            append_event(db, campaign.id, "scene_changed", {"scene_id": scene.id, "name": scene.name},
                         session_id=session.id)
    commit(db)
    return session


@router.post("/campaigns/{campaign_id}/sessions/{session_id}/close", response_model=SessionOut)
def close_session(campaign: CampaignDep, session_id: str, body: SessionClose, db: Db) -> GameSession:
    session = _session(db, campaign, session_id)
    summary = body.summary or {}
    if not summary and body.generate_summary:
        from app.ai.summary import summarize_session

        summary = summarize_session(db, session)
    session_service.close_session(db, session, summary)
    commit(db)
    return session


# --------------------------------------------------------------- eventos ---
@router.get("/campaigns/{campaign_id}/events", response_model=list[dict[str, Any]])
def list_events(campaign: CampaignDep, db: Db, dm: IsDm, after_seq: int = 0, limit: int = 200) -> list[dict[str, Any]]:
    query = select(Event).where(Event.campaign_id == campaign.id, Event.seq > after_seq)
    if not dm:
        query = query.where(Event.visibility == "public")
    rows = db.scalars(query.order_by(Event.seq.desc()).limit(min(limit, 1000)))
    return [event_to_dict(e) for e in reversed(list(rows))]


# --------------------------------------------------------------- tiradas ---
@router.get("/campaigns/{campaign_id}/rolls", response_model=list[dict[str, Any]])
def list_rolls(campaign: CampaignDep, db: Db, dm: IsDm, status: str | None = None) -> list[dict[str, Any]]:
    query = select(DiceRoll).where(DiceRoll.campaign_id == campaign.id)
    if status:
        query = query.where(DiceRoll.status == status)
    rows = db.scalars(query.order_by(DiceRoll.created_at.desc()).limit(100))
    result = []
    for roll in rows:
        data = roll_service.public_roll(roll)
        if dm:
            data["dc"] = roll.dc
        result.append(data)
    return result


@router.post("/campaigns/{campaign_id}/rolls", response_model=dict[str, Any], status_code=201)
def request_roll(campaign: DmCampaign, body: CheckRequest, db: Db) -> dict[str, Any]:
    """El DM humano pide una prueba (la IA lo hace desde el motor narrativo)."""
    session = require_open_session(db, campaign)
    character = get_character(db, campaign, body.character_id)
    roll = roll_service.request_check(
        db, session, character, kind=CheckKind(body.kind), skill=body.skill, ability=body.ability, dc=body.dc,
        difficulty=body.difficulty, dc_public=body.dc_public, advantage=body.advantage, reason=body.reason,
        requested_by="dm",
    )
    commit(db)
    return roll_service.public_roll(roll)


@router.post("/campaigns/{campaign_id}/rolls/{roll_id}/resolve", response_model=dict[str, Any])
def resolve_roll(campaign: CampaignDep, roll_id: str, body: RollResolve, db: Db) -> dict[str, Any]:
    roll = db.get(DiceRoll, roll_id)
    if roll is None or roll.campaign_id != campaign.id:
        raise NotFound("La tirada no existe.")
    roll_service.resolve_check(db, campaign, roll, body.mode, body.values)
    commit(db)
    result = roll_service.public_roll(roll)
    result["breakdown"] = roll.context.get("breakdown", "")
    from app.ai.turn import after_roll

    after_roll(db, campaign, roll)
    return result


@router.post("/campaigns/{campaign_id}/rolls/{roll_id}/void", status_code=204)
def void_roll(campaign: DmCampaign, roll_id: str, db: Db) -> None:
    roll = db.get(DiceRoll, roll_id)
    if roll is None or roll.campaign_id != campaign.id:
        raise NotFound("La tirada no existe.")
    roll_service.void_roll(db, roll, "anulada por el DM")
    session = db.get(GameSession, roll.session_id) if roll.session_id else None
    if session and session.state == "awaiting_roll" and not roll_service.pending_rolls(db, campaign.id):
        session.state = "exploring"
    commit(db)


@router.post("/campaigns/{campaign_id}/rolls/free", response_model=dict[str, Any], status_code=201)
def free_roll(campaign: CampaignDep, body: FreeRoll, db: Db) -> dict[str, Any]:
    session = session_service.open_session(db, campaign.id)
    if body.character_id:
        get_character(db, campaign, body.character_id)
    result = roll_service.free_roll(db, campaign, session, body.expression, body.mode, body.values, body.label,
                                    body.character_id)
    commit(db)
    return result


# --------------------------------------------------------------- acciones --
@router.post("/campaigns/{campaign_id}/actions", response_model=dict[str, Any], status_code=202)
def player_action(campaign: CampaignDep, body: PlayerAction, db: Db) -> dict[str, Any]:
    """Acción libre de un personaje. La IA la interpreta en segundo plano y responde por WebSocket."""
    session = require_open_session(db, campaign)
    if session.state == "awaiting_roll":
        raise Conflict("Hay una tirada pendiente. Resuélvela antes de declarar otra acción.")
    character = get_character(db, campaign, body.character_id)
    event = append_event(
        db, campaign.id, "player_action",
        {"character_id": character.id, "name": character.name, "player_id": body.player_id, "text": body.text,
         "target": body.target},
        actor_kind="player", actor_id=body.player_id, session_id=session.id,
    )
    commit(db)
    from app.ai.turn import schedule_turn

    schedule_turn(campaign.id, session.id, event.id)
    return {"event_id": event.id, "seq": event.seq, "status": "accepted"}
