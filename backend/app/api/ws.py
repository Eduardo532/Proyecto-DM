"""WebSocket de la mesa: envía eventos en tiempo real.

``/ws/campaigns/{id}`` recibe solo eventos públicos; con ``?dm_token=`` recibe también los del DM.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.dm_auth import tokens
from app.services.hub import hub

router = APIRouter()


@router.websocket("/ws/campaigns/{campaign_id}")
async def table_socket(websocket: WebSocket, campaign_id: str, dm_token: str | None = None) -> None:
    await websocket.accept()
    is_dm = tokens.check(dm_token, campaign_id)
    subscriber = hub.subscribe(campaign_id, is_dm)
    await websocket.send_json({"kind": "hello", "dm": is_dm})

    async def pump() -> None:
        while True:
            message = await subscriber.queue.get()
            await websocket.send_json(message)

    sender = asyncio.create_task(pump())
    try:
        while True:
            # Mantiene la conexión viva; el cliente puede enviar "ping".
            text = await websocket.receive_text()
            if text == "ping":
                await websocket.send_json({"kind": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        sender.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sender
        hub.unsubscribe(subscriber)
