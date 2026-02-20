from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from redis.asyncio import Redis

from backend.core.config import BackendSettings, get_settings


class RequestRateLimiter:
    def __init__(self, settings: BackendSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self._redis: Redis | None = None
        self._local_lock = asyncio.Lock()
        self._local_windows: dict[tuple[str, ...], deque[float]] = defaultdict(deque)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def check_limit(
        self,
        *,
        scope: str,
        identity: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        if limit <= 0:
            return False, 0

        redis_result = await self._check_limit_redis(
            scope=scope,
            identity=identity,
            limit=limit,
            window_seconds=window_seconds,
        )
        if redis_result is not None:
            return redis_result

        return await self._check_limit_local(
            key=(scope, identity),
            limit=limit,
            window_seconds=window_seconds,
        )

    async def record_authz_failure(
        self,
        *,
        scope: str,
        identity: str,
        window_seconds: int,
    ) -> int:
        redis_count = await self._record_authz_failure_redis(
            scope=scope,
            identity=identity,
            window_seconds=window_seconds,
        )
        if redis_count is not None:
            return redis_count

        return await self._record_authz_failure_local(
            key=(scope, identity),
            window_seconds=window_seconds,
        )

    async def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def _check_limit_redis(
        self,
        *,
        scope: str,
        identity: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int] | None:
        try:
            redis = await self._client()
            bucket = int(time.time() // max(1, window_seconds))
            key = (
                f"{self.settings.IPC_STREAM_PREFIX}:rl:{scope}:"
                f"{_sanitize_identity(identity)}:{bucket}"
            )
            count = int(await redis.incr(key))
            if count == 1:
                await redis.expire(key, max(2, window_seconds + 2))
            return count <= limit, count
        except Exception:
            return None

    async def _check_limit_local(
        self,
        *,
        key: tuple[str, str],
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - max(1, window_seconds)
        async with self._local_lock:
            queue = self._local_windows[key]
            while queue and queue[0] < cutoff:
                queue.popleft()
            queue.append(now)
            count = len(queue)
            return count <= limit, count

    async def _record_authz_failure_redis(
        self,
        *,
        scope: str,
        identity: str,
        window_seconds: int,
    ) -> int | None:
        try:
            redis = await self._client()
            bucket = int(time.time() // max(1, window_seconds))
            key = (
                f"{self.settings.IPC_STREAM_PREFIX}:authzfail:{scope}:"
                f"{_sanitize_identity(identity)}:{bucket}"
            )
            count = int(await redis.incr(key))
            if count == 1:
                await redis.expire(key, max(2, window_seconds + 2))
            return count
        except Exception:
            return None

    async def _record_authz_failure_local(
        self,
        *,
        key: tuple[str, str],
        window_seconds: int,
    ) -> int:
        now = time.time()
        cutoff = now - max(1, window_seconds)
        compound_key = ("authzfail", *key)
        async with self._local_lock:
            queue = self._local_windows[compound_key]
            while queue and queue[0] < cutoff:
                queue.popleft()
            queue.append(now)
            return len(queue)


def _sanitize_identity(value: str) -> str:
    return value.replace(":", "_").replace("/", "_")


rate_limiter = RequestRateLimiter()
