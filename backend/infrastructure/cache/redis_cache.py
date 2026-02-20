from __future__ import annotations

import json
from collections.abc import Mapping

from redis.asyncio import Redis

from backend.core.config import get_settings


class RedisCache:
    """Small Redis cache wrapper with optional tag invalidation."""

    def __init__(self):
        self.settings = get_settings()
        self._redis: Redis | None = None

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def get_json(self, key: str):
        if not self.settings.BACKEND_CACHE_ENABLED:
            return None
        try:
            client = await self._client()
            raw = await client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            return None

    async def set_json(
        self,
        *,
        key: str,
        value,
        ttl_seconds: int,
        tags: set[str] | None = None,
    ) -> None:
        if not self.settings.BACKEND_CACHE_ENABLED:
            return
        ttl = max(1, int(ttl_seconds))
        try:
            client = await self._client()
            payload = json.dumps(value, separators=(",", ":"))
            await client.set(key, payload, ex=ttl)
            if tags:
                pipe = client.pipeline()
                for tag in tags:
                    tag_key = self._tag_key(tag)
                    pipe.sadd(tag_key, key)
                    pipe.expire(tag_key, max(ttl + 300, 300))
                await pipe.execute()
        except Exception:
            return

    async def invalidate_tags(self, *tags: str) -> None:
        if not self.settings.BACKEND_CACHE_ENABLED:
            return
        cleaned = {tag.strip() for tag in tags if tag and tag.strip()}
        if not cleaned:
            return
        try:
            client = await self._client()
            for tag in cleaned:
                tag_key = self._tag_key(tag)
                keys = await client.smembers(tag_key)
                if keys:
                    await client.delete(*keys)
                await client.delete(tag_key)
        except Exception:
            return

    async def invalidate_key(self, key: str) -> None:
        if not self.settings.BACKEND_CACHE_ENABLED:
            return
        try:
            client = await self._client()
            await client.delete(key)
        except Exception:
            return

    def build_key(self, scope: str, params: Mapping[str, object] | None = None) -> str:
        if not params:
            return f"{self.settings.BACKEND_CACHE_PREFIX}:{scope}"
        encoded_parts: list[str] = []
        for key, value in sorted(params.items()):
            encoded_parts.append(f"{key}={self._encode_param(value)}")
        encoded = "&".join(encoded_parts)
        return f"{self.settings.BACKEND_CACHE_PREFIX}:{scope}:{encoded}"

    @staticmethod
    def user_tag(user_id: int) -> str:
        return f"user:{user_id}"

    def _tag_key(self, tag: str) -> str:
        return f"{self.settings.BACKEND_CACHE_PREFIX}:tag:{tag}"

    async def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.settings.REDIS_URL, decode_responses=True)
        return self._redis

    @staticmethod
    def _encode_param(value: object) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float, str)):
            return str(value)
        if isinstance(value, (list, tuple, set)):
            return ",".join(str(item) for item in value)
        return str(value)


cache = RedisCache()
