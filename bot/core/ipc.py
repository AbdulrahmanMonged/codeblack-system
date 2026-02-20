"""
IPC layer for bidirectional communication between the Discord bot
and a FastAPI backend via Redis Streams + Pub/Sub.

Pub/Sub: Real-time fire-and-forget notifications.
Streams: Persistent, ordered message queues with consumer groups and ack.

Usage from Bot:
    ipc = IPCManager()
    await ipc.initialize()

    # Publish real-time event
    await ipc.publish_event("player_login", {"player": "John", "time": "..."})

    # Add to persistent stream (FastAPI will consume later)
    await ipc.stream_push("events", {"type": "join", "player": "John"})

    # Listen for commands from FastAPI
    async for msg in ipc.listen_commands("bot-worker"):
        await handle_command(msg)

Usage from FastAPI:
    # Read events stream
    msgs = await ipc.stream_read("events", last_id="0")

    # Push command to bot
    await ipc.stream_push("commands", {"action": "refresh_session"})

    # Subscribe to real-time events
    async for msg in ipc.subscribe_events():
        await broadcast_to_websockets(msg)
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Callable

from bot.config import get_settings
from .redis import RedisManager

logger = logging.getLogger(__name__)


class IPCManager:
    """
    Inter-Process Communication via Redis Streams + Pub/Sub.
    """

    def __init__(self):
        settings = get_settings()
        prefix = settings.IPC_STREAM_PREFIX

        # Pub/Sub channels
        self.CH_PLAYER_EVENT = f"{prefix}:pubsub:player"
        self.CH_FORUM_UPDATE = f"{prefix}:pubsub:forum"
        self.CH_BOT_STATUS = f"{prefix}:pubsub:status"

        # Streams
        self.STREAM_COMMANDS = f"{prefix}:stream:commands"  # FastAPI → Bot
        self.STREAM_RESPONSES = f"{prefix}:stream:responses"  # Bot → FastAPI
        self.STREAM_EVENTS = f"{prefix}:stream:events"  # Bot → FastAPI (log)

        self._listeners: list[asyncio.Task] = []

    async def initialize(self) -> None:
        """Create consumer groups for streams (idempotent)."""
        await RedisManager.xgroup_create(self.STREAM_COMMANDS, "bot-workers")
        await RedisManager.xgroup_create(self.STREAM_EVENTS, "api-workers")
        await RedisManager.xgroup_create(self.STREAM_RESPONSES, "api-workers")
        logger.info("IPC streams and consumer groups initialized")

    # ── Pub/Sub (fire-and-forget notifications) ────────────

    async def publish_event(self, event_type: str, data: dict) -> None:
        """Publish a real-time event notification."""
        message = {"type": event_type, **data}
        await RedisManager.publish(self.CH_PLAYER_EVENT, message)

    async def publish_forum_update(self, data: dict) -> None:
        await RedisManager.publish(self.CH_FORUM_UPDATE, data)

    async def publish_status(self, status: str, details: dict | None = None) -> None:
        message = {"status": status}
        if details:
            message.update(details)
        await RedisManager.publish(self.CH_BOT_STATUS, message)

    async def subscribe(
        self, *channels: str, callback: Callable[[str, dict], Any]
    ) -> asyncio.Task:
        """Subscribe to Pub/Sub channels with a callback."""

        async def _listener():
            pubsub = RedisManager.get_pubsub()
            await pubsub.subscribe(*channels)
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        channel = message["channel"]
                        try:
                            data = json.loads(message["data"])
                        except (json.JSONDecodeError, TypeError):
                            data = {"raw": message["data"]}
                        await callback(channel, data)
            except asyncio.CancelledError:
                pass
            finally:
                await pubsub.unsubscribe(*channels)
                await pubsub.aclose()

        task = asyncio.create_task(_listener())
        self._listeners.append(task)
        return task

    # ── Streams (persistent queues) ────────────────────────

    async def stream_push(
        self, stream_name: str, data: dict, maxlen: int = 10000
    ) -> str | None:
        """Push a message to a stream."""
        stream_key = self._resolve_stream(stream_name)
        return await RedisManager.xadd(stream_key, data, maxlen=maxlen)

    async def stream_read(
        self, stream_name: str, last_id: str = "0", count: int = 10
    ) -> list:
        """Read messages from a stream (standalone, no consumer group)."""
        stream_key = self._resolve_stream(stream_name)
        return await RedisManager.xread({stream_key: last_id}, count=count)

    async def listen_commands(
        self, consumer_name: str, count: int = 5, block_ms: int = 5000
    ) -> AsyncGenerator[dict, None]:
        """
        Listen for commands from FastAPI via consumer group.

        Yields dicts with 'id' and 'data' keys.
        Auto-acknowledges after processing.
        """
        group = "bot-workers"
        stream = self.STREAM_COMMANDS

        while True:
            try:
                messages = await RedisManager.xreadgroup(
                    group=group,
                    consumer=consumer_name,
                    streams={stream: ">"},
                    count=count,
                    block=block_ms,
                )

                for stream_name, entries in messages:
                    for entry_id, fields in entries:
                        # Deserialize JSON values
                        data = {}
                        for k, v in fields.items():
                            try:
                                data[k] = json.loads(v)
                            except (json.JSONDecodeError, TypeError):
                                data[k] = v

                        yield {"id": entry_id, "data": data}
                        await RedisManager.xack(stream, group, entry_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading commands: {e}")
                await asyncio.sleep(1)

    async def push_event(self, event_type: str, data: dict) -> str | None:
        """Push an event to the events stream (for FastAPI to consume)."""
        return await self.stream_push(
            "events", {"type": event_type, **data}
        )

    async def push_response(self, command_id: str, result: dict) -> str | None:
        """Push a response to the responses stream."""
        return await self.stream_push(
            "responses", {"command_id": command_id, **result}
        )

    # ── Helpers ────────────────────────────────────────────

    def _resolve_stream(self, name: str) -> str:
        """Map short name to full stream key."""
        mapping = {
            "commands": self.STREAM_COMMANDS,
            "responses": self.STREAM_RESPONSES,
            "events": self.STREAM_EVENTS,
        }
        return mapping.get(name, name)

    async def close(self) -> None:
        for task in self._listeners:
            task.cancel()
        if self._listeners:
            await asyncio.gather(*self._listeners, return_exceptions=True)
        self._listeners.clear()
        logger.info("IPC listeners stopped")
