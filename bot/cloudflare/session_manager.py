from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from bot.config import get_settings

from .capsolver_strategy import CapsolverStrategy

logger = logging.getLogger(__name__)

SESSION_REDIS_PREFIX = "codeblack:cf:session"
SESSION_REDIS_TTL_SECONDS = 24 * 60 * 60


@dataclass
class _SessionEntry:
    data: dict
    expires_at: datetime


class SessionManager:
    """Cloudflare-aware session cache with optional Redis persistence."""

    def __init__(self, ttl_minutes: int = 20):
        self._ttl = max(1, int(ttl_minutes))
        self._entries: dict[str, _SessionEntry] = {}
        self._redis = None
        self._lock = asyncio.Lock()

        settings = get_settings()
        self._login_url = "https://cit.gg/index.php?action=login"
        self._cit_username = settings.CIT_USERNAME
        self._cit_password = settings.CIT_PASSWORD
        self._strategy = (
            CapsolverStrategy(
                api_key=settings.CAPSOLVER_API_KEY,
                proxy=settings.CF_PROXY,
            )
            if settings.CAPSOLVER_API_KEY
            else None
        )

    def set_redis(self, redis_client) -> None:
        self._redis = redis_client

    def _key_for(self, url: str) -> str:
        parsed = urlparse(url)
        return (parsed.netloc or parsed.path or "default").strip().lower()

    def _redis_key(self, key: str) -> str:
        return f"{SESSION_REDIS_PREFIX}:{key}"

    def _is_valid_entry(self, entry: _SessionEntry | None) -> bool:
        if entry is None:
            return False
        now = datetime.now(timezone.utc)
        return entry.expires_at > now

    async def _load_from_redis(self, key: str) -> dict | None:
        if self._redis is None:
            return None
        try:
            cached = await self._redis.get(self._redis_key(key), as_json=True)
            if isinstance(cached, dict):
                return cached
        except Exception as exc:
            logger.debug("Redis session read failed for %s: %s", key, exc)
        return None

    async def _store_in_redis(self, key: str, data: dict) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set(
                self._redis_key(key),
                data,
                expire=SESSION_REDIS_TTL_SECONDS,
            )
        except Exception as exc:
            logger.debug("Redis session write failed for %s: %s", key, exc)

    async def get_session_data(self, url: str) -> dict | None:
        key = self._key_for(url)
        entry = self._entries.get(key)
        if self._is_valid_entry(entry):
            return dict(entry.data)

        self._entries.pop(key, None)

        cached = await self._load_from_redis(key)
        if not isinstance(cached, dict):
            return None

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self._ttl)
        self._entries[key] = _SessionEntry(data=dict(cached), expires_at=expires_at)
        return dict(cached)

    async def set_session_data(self, url: str, data: dict) -> None:
        key = self._key_for(url)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self._ttl)
        payload = dict(data)
        self._entries[key] = _SessionEntry(data=payload, expires_at=expires_at)
        await self._store_in_redis(key, payload)

    async def get_session(
        self,
        *,
        force_refresh: bool = False,
        url: str = "https://cit.gg/",
    ) -> dict | None:
        """Get cached session or try to bootstrap one with Capsolver."""
        if not force_refresh:
            cached = await self.get_session_data(url)
            if cached:
                return cached

        if self._strategy is None:
            return None

        async with self._lock:
            if not force_refresh:
                cached = await self.get_session_data(url)
                if cached:
                    return cached

            solved = await self._create_session(url)
            if solved:
                await self.set_session_data(url, solved)
            return solved

    async def _create_session(self, url: str) -> dict | None:
        target_url = url if urlparse(url).scheme else "https://cit.gg/"
        try:
            if self._cit_username and self._cit_password:
                result = await self._strategy.login_and_solve(
                    login_url=self._login_url,
                    username=self._cit_username,
                    password=self._cit_password,
                )
            else:
                result = await self._strategy.solve(target_url)
        except Exception as exc:
            logger.error("Failed solving Cloudflare challenge: %s", exc)
            return None

        if not isinstance(result, dict):
            return None

        cookies = result.get("cookies")
        if not isinstance(cookies, dict):
            cookies = {}

        normalized = {
            "cookies": {str(k): str(v) for k, v in cookies.items()},
            "user_agent": str(result.get("user_agent") or ""),
        }
        return normalized

    async def clear(self, url: str) -> None:
        key = self._key_for(url)
        self._entries.pop(key, None)
        if self._redis is not None:
            try:
                await self._redis.delete(self._redis_key(key))
            except Exception as exc:
                logger.debug("Redis session delete failed for %s: %s", key, exc)

    async def clear_session(self, url: str | None = None) -> None:
        """Backward-compatible alias used by older callers."""
        if url:
            await self.clear(url)
            return

        keys = list(self._entries.keys())
        self._entries.clear()
        if self._redis is not None:
            for key in keys or ["cit.gg", "www.cit.gg", "default"]:
                try:
                    await self._redis.delete(self._redis_key(key))
                except Exception:
                    pass
