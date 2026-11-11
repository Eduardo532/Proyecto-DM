"""Difusión en tiempo real por WebSocket.

Las rutas HTTP se ejecutan en hilos; cada conexión WebSocket tiene una cola en el bucle de
eventos. ``publish`` es seguro desde cualquier hilo.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass(eq=False)
class Subscriber:
    campaign_id: str
    is_dm: bool
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)


class Hub:
    def __init__(self) -> None:
        self._subscribers: set[Subscriber] = set()
        self._lock = threading.Lock()

    def subscribe(self, campaign_id: str, is_dm: bool) -> Subscriber:
        sub = Subscriber(campaign_id, is_dm, asyncio.get_running_loop())
        with self._lock:
            self._subscribers.add(sub)
        return sub

    def unsubscribe(self, sub: Subscriber) -> None:
        with self._lock:
            self._subscribers.discard(sub)

    def publish(self, campaign_id: str, message: dict[str, Any], visibility: str = "public") -> None:
        with self._lock:
            targets = [s for s in self._subscribers if s.campaign_id == campaign_id]
        for sub in targets:
            if visibility != "public" and not sub.is_dm:
                continue
            try:
                sub.loop.call_soon_threadsafe(sub.queue.put_nowait, message)
            except RuntimeError:
                self.unsubscribe(sub)  # bucle cerrado

    def count(self, campaign_id: str) -> int:
        with self._lock:
            return sum(1 for s in self._subscribers if s.campaign_id == campaign_id)


hub = Hub()
