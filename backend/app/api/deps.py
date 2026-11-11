"""Dependencias comunes de las rutas."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.db import Database
from app.models import Campaign
from app.services.dm_auth import tokens
from app.services.errors import Forbidden, NotFound
from app.services.events import flush_broadcasts


def get_db(request: Request) -> Iterator[Session]:
    database: Database = request.app.state.db
    with database.session_factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


Db = Annotated[Session, Depends(get_db)]


def commit(db: Session) -> None:
    """Confirma la transacción y envía a la mesa los eventos generados."""
    db.commit()
    flush_broadcasts(db)


def get_campaign(campaign_id: str, db: Db) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFound("La campaña no existe.")
    return campaign


CampaignDep = Annotated[Campaign, Depends(get_campaign)]


def is_dm(campaign: CampaignDep, x_dm_token: Annotated[str | None, Header()] = None) -> bool:
    return tokens.check(x_dm_token, campaign.id)


def require_dm(campaign: CampaignDep, x_dm_token: Annotated[str | None, Header()] = None) -> Campaign:
    if not tokens.check(x_dm_token, campaign.id):
        raise Forbidden("Hace falta el modo DM para esta operación.")
    return campaign


IsDm = Annotated[bool, Depends(is_dm)]
DmCampaign = Annotated[Campaign, Depends(require_dm)]
