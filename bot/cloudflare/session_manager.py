from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse


@dataclass
class _SessionEntry:
    data: dict
    expires_at: datetime


class SessionManager:
    """Simple in-memory session cache with optional Redis integration hook."""

    def __init__(self, ttl_minutes: int = 20):
        self._ttl = max(1, int(ttl_minutes))
        self._entries: dict[str, _SessionEntry] = {}
        self._redis = None

    def set_redis(self, redis_client) -> None:
        self._redis = redis_client

    def _key_for(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or parsed.path or "default"

    async def get_session_data(self, url: str) -> dict | None:
        key = self._key_for(url)
        entry = self._entries.get(key)
        if not entry:
            return None
        now = datetime.now(timezone.utc)
        if entry.expires_at <= now:
            self._entries.pop(key, None)
            return None
        return dict(entry.data)

    async def set_session_data(self, url: str, data: dict) -> None:
        key = self._key_for(url)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self._ttl)
        self._entries[key] = _SessionEntry(data=dict(data), expires_at=expires_at)

    async def clear(self, url: str) -> None:
        self._entries.pop(self._key_for(url), None)
