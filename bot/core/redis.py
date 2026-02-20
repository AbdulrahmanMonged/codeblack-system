"""
Redis manager with connection pooling, JSON serialization,
and Redis Streams support for IPC.
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from bot.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Async Redis manager with support for strings, hashes, lists, sets,
    and Redis Streams.
    """

    _instance = None
    _pool: aioredis.ConnectionPool | None = None
    _client: aioredis.Redis | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls, redis_url: str | None = None) -> None:
        if cls._pool is not None:
            logger.warning("Redis pool already initialized")
            return

        if redis_url is None:
            redis_url = get_settings().REDIS_URL

        try:
            cls._pool = aioredis.ConnectionPool.from_url(
                redis_url,
                max_connections=10,
                decode_responses=True,
                encoding="utf-8",
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True,
            )
            cls._client = aioredis.Redis(connection_pool=cls._pool)
            await cls._client.ping()
            logger.info("Redis connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise

    @classmethod
    async def close(cls) -> None:
        if cls._client:
            await cls._client.aclose()
            cls._client = None
        if cls._pool:
            await cls._pool.aclose()
            cls._pool = None
        logger.info("Redis closed")

    @classmethod
    def get_client(cls) -> aioredis.Redis:
        if cls._client is None:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return cls._client

    # ── Serialization helpers ──────────────────────────────

    @staticmethod
    def _serialize(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    @staticmethod
    def _deserialize(value: str | None, as_json: bool = False) -> Any:
        if value is None:
            return None
        if as_json:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    # ── String operations ──────────────────────────────────

    @classmethod
    async def set(cls, key: str, value: Any, expire: int | None = None) -> bool:
        try:
            client = cls.get_client()
            await client.set(key, cls._serialize(value), ex=expire)
            return True
        except Exception as e:
            logger.error(f"Redis SET {key}: {e}")
            return False

    @classmethod
    async def get(cls, key: str, as_json: bool = False) -> Any:
        try:
            client = cls.get_client()
            value = await client.get(key)
            return cls._deserialize(value, as_json)
        except Exception as e:
            logger.error(f"Redis GET {key}: {e}")
            return None

    @classmethod
    async def delete(cls, *keys: str) -> int:
        try:
            return await cls.get_client().delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE: {e}")
            return 0

    @classmethod
    async def exists(cls, *keys: str) -> int:
        try:
            return await cls.get_client().exists(*keys)
        except Exception as e:
            logger.error(f"Redis EXISTS: {e}")
            return 0

    @classmethod
    async def expire(cls, key: str, seconds: int) -> bool:
        try:
            return await cls.get_client().expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE: {e}")
            return False

    @classmethod
    async def incr(cls, key: str, amount: int = 1) -> int | None:
        try:
            return await cls.get_client().incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR: {e}")
            return None

    # ── Hash operations ────────────────────────────────────

    @classmethod
    async def hset(cls, name: str, key: str, value: Any) -> int:
        try:
            return await cls.get_client().hset(name, key, cls._serialize(value))
        except Exception as e:
            logger.error(f"Redis HSET {name}:{key}: {e}")
            return 0

    @classmethod
    async def hget(cls, name: str, key: str, as_json: bool = False) -> Any:
        try:
            value = await cls.get_client().hget(name, key)
            return cls._deserialize(value, as_json)
        except Exception as e:
            logger.error(f"Redis HGET {name}:{key}: {e}")
            return None

    @classmethod
    async def hgetall(cls, name: str) -> dict:
        try:
            return await cls.get_client().hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL {name}: {e}")
            return {}

    @classmethod
    async def hdel(cls, name: str, *keys: str) -> int:
        try:
            return await cls.get_client().hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis HDEL: {e}")
            return 0

    @classmethod
    async def hincrby(cls, name: str, key: str, amount: int = 1) -> int | None:
        try:
            return await cls.get_client().hincrby(name, key, amount)
        except Exception as e:
            logger.error(f"Redis HINCRBY: {e}")
            return None

    @classmethod
    async def hexists(cls, name: str, key: str) -> bool:
        try:
            return await cls.get_client().hexists(name, key)
        except Exception as e:
            logger.error(f"Redis HEXISTS: {e}")
            return False

    @classmethod
    async def hmset(cls, name: str, mapping: dict) -> bool:
        try:
            serialized = {k: cls._serialize(v) for k, v in mapping.items()}
            await cls.get_client().hset(name, mapping=serialized)
            return True
        except Exception as e:
            logger.error(f"Redis HMSET {name}: {e}")
            return False

    # ── List operations ────────────────────────────────────

    @classmethod
    async def lpush(cls, key: str, *values: Any) -> int:
        try:
            return await cls.get_client().lpush(
                key, *[cls._serialize(v) for v in values]
            )
        except Exception as e:
            logger.error(f"Redis LPUSH: {e}")
            return 0

    @classmethod
    async def rpush(cls, key: str, *values: Any) -> int:
        try:
            return await cls.get_client().rpush(
                key, *[cls._serialize(v) for v in values]
            )
        except Exception as e:
            logger.error(f"Redis RPUSH: {e}")
            return 0

    @classmethod
    async def lpop(cls, key: str, as_json: bool = False) -> Any:
        try:
            value = await cls.get_client().lpop(key)
            return cls._deserialize(value, as_json)
        except Exception as e:
            logger.error(f"Redis LPOP: {e}")
            return None

    @classmethod
    async def rpop(cls, key: str, as_json: bool = False) -> Any:
        try:
            value = await cls.get_client().rpop(key)
            return cls._deserialize(value, as_json)
        except Exception as e:
            logger.error(f"Redis RPOP: {e}")
            return None

    @classmethod
    async def lrange(cls, key: str, start: int = 0, end: int = -1) -> list:
        try:
            return await cls.get_client().lrange(key, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE: {e}")
            return []

    # ── Set operations ─────────────────────────────────────

    @classmethod
    async def sadd(cls, key: str, *members: Any) -> int:
        try:
            return await cls.get_client().sadd(
                key, *[cls._serialize(m) for m in members]
            )
        except Exception as e:
            logger.error(f"Redis SADD: {e}")
            return 0

    @classmethod
    async def srem(cls, key: str, *members: Any) -> int:
        try:
            return await cls.get_client().srem(
                key, *[cls._serialize(m) for m in members]
            )
        except Exception as e:
            logger.error(f"Redis SREM: {e}")
            return 0

    @classmethod
    async def smembers(cls, key: str) -> set:
        try:
            return await cls.get_client().smembers(key)
        except Exception as e:
            logger.error(f"Redis SMEMBERS: {e}")
            return set()

    @classmethod
    async def sismember(cls, key: str, member: Any) -> bool:
        try:
            return await cls.get_client().sismember(key, cls._serialize(member))
        except Exception as e:
            logger.error(f"Redis SISMEMBER: {e}")
            return False

    # ── Scan ───────────────────────────────────────────────

    @classmethod
    async def scan_keys(cls, pattern: str) -> list:
        try:
            client = cls.get_client()
            keys = []
            cursor = 0
            while True:
                cursor, batch = await client.scan(
                    cursor=cursor, match=pattern, count=100
                )
                keys.extend(batch)
                if cursor == 0:
                    break
            return keys
        except Exception as e:
            logger.error(f"Redis SCAN {pattern}: {e}")
            return []

    # ── Stream operations (for IPC) ────────────────────────

    @classmethod
    async def xadd(
        cls, stream: str, fields: dict, maxlen: int | None = 10000
    ) -> str | None:
        """Add entry to a stream. Returns the entry ID."""
        try:
            serialized = {k: cls._serialize(v) for k, v in fields.items()}
            entry_id = await cls.get_client().xadd(
                stream, serialized, maxlen=maxlen, approximate=True
            )
            return entry_id
        except Exception as e:
            logger.error(f"Redis XADD {stream}: {e}")
            return None

    @classmethod
    async def xread(
        cls,
        streams: dict[str, str],
        count: int = 10,
        block: int | None = None,
    ) -> list:
        """Read from streams. streams = {"stream_name": "last_id"}."""
        try:
            return await cls.get_client().xread(
                streams=streams, count=count, block=block
            )
        except Exception as e:
            logger.error(f"Redis XREAD: {e}")
            return []

    @classmethod
    async def xgroup_create(
        cls, stream: str, group: str, id: str = "0", mkstream: bool = True
    ) -> bool:
        """Create a consumer group on a stream."""
        try:
            await cls.get_client().xgroup_create(
                stream, group, id=id, mkstream=mkstream
            )
            return True
        except Exception as e:
            if "BUSYGROUP" in str(e):
                return True  # Group already exists
            logger.error(f"Redis XGROUP CREATE {stream}/{group}: {e}")
            return False

    @classmethod
    async def xreadgroup(
        cls,
        group: str,
        consumer: str,
        streams: dict[str, str],
        count: int = 10,
        block: int | None = None,
    ) -> list:
        """Read from stream as part of a consumer group."""
        try:
            return await cls.get_client().xreadgroup(
                groupname=group,
                consumername=consumer,
                streams=streams,
                count=count,
                block=block,
            )
        except Exception as e:
            logger.error(f"Redis XREADGROUP: {e}")
            return []

    @classmethod
    async def xack(cls, stream: str, group: str, *ids: str) -> int:
        """Acknowledge processed messages in a consumer group."""
        try:
            return await cls.get_client().xack(stream, group, *ids)
        except Exception as e:
            logger.error(f"Redis XACK: {e}")
            return 0

    # ── Pub/Sub ────────────────────────────────────────────

    @classmethod
    async def publish(cls, channel: str, message: Any) -> int:
        """Publish a message to a Pub/Sub channel."""
        try:
            return await cls.get_client().publish(channel, cls._serialize(message))
        except Exception as e:
            logger.error(f"Redis PUBLISH {channel}: {e}")
            return 0

    @classmethod
    def get_pubsub(cls) -> aioredis.client.PubSub:
        """Get a Pub/Sub instance for subscribing."""
        return cls.get_client().pubsub()
