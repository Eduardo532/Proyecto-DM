"""Modo DM: PIN con hash y tokens temporales en memoria."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time

TOKEN_TTL_SECONDS = 15 * 60
_ITERATIONS = 200_000


def hash_pin(pin: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), _ITERATIONS).hex()
    return f"pbkdf2${salt}${digest}"


def verify_pin(pin: str, stored: str | None) -> bool:
    if not stored:
        return True  # campaña sin PIN: el modo DM está abierto
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), _ITERATIONS).hex()
    return hmac.compare_digest(candidate, digest)


class TokenStore:
    def __init__(self) -> None:
        self._tokens: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def issue(self, campaign_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = (campaign_id, time.monotonic() + TOKEN_TTL_SECONDS)
        return token

    def check(self, token: str | None, campaign_id: str) -> bool:
        """Valida el token y renueva su caducidad (15 minutos desde el último uso)."""
        if not token:
            return False
        with self._lock:
            entry = self._tokens.get(token)
            if not entry or entry[0] != campaign_id or entry[1] < time.monotonic():
                self._tokens.pop(token, None)
                return False
            self._tokens[token] = (campaign_id, time.monotonic() + TOKEN_TTL_SECONDS)
            return True

    def revoke(self, token: str) -> None:
        with self._lock:
            self._tokens.pop(token, None)


tokens = TokenStore()
