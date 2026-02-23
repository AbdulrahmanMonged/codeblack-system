from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from bot.config import get_settings
from bot.core.celery_app import celery_app
from bot.core.ipc import IPCManager
from bot.core.redis import RedisManager

logger = logging.getLogger(__name__)


class IPCCommandHandler:
    def __init__(self, ipc: IPCManager, bot=None):
        settings = get_settings()
        prefix = settings.IPC_STREAM_PREFIX
        self.ipc = ipc
        self.bot = bot
        self.consumer_name = f"discord-bot-{uuid4().hex[:8]}"
        self.features_hash_key = f"{prefix}:runtime:features"
        self.channels_hash_key = f"{prefix}:runtime:channels"

    async def run(self) -> None:
        logger.info("IPC command handler started with consumer=%s", self.consumer_name)
        async for message in self.ipc.listen_commands(self.consumer_name):
            await self._handle_message(message)

    async def _handle_message(self, message: dict) -> None:
        command_stream_id = message.get("id")
        data = message.get("data", {})
        request_id = str(data.get("request_id", ""))
        response_command_id = request_id or str(command_stream_id)
        command_type = str(data.get("type", ""))

        try:
            if command_type == "toggle_service":
                result = await self._toggle_service(data)
            elif command_type == "set_channel_config":
                result = await self._set_channel_config(data)
            elif command_type == "trigger_forum_sync":
                result = self._trigger_forum_sync()
            elif command_type == "trigger_cop_scores_refresh":
                result = self._trigger_cop_scores_refresh()
            elif command_type == "publish_activity_forum":
                result = await self._publish_activity_forum(data)
            else:
                raise ValueError(f"Unsupported command type: {command_type}")

            await self.ipc.push_response(
                response_command_id,
                {
                    "type": "command_ack",
                    "ok": True,
                    "request_id": request_id,
                    "command_type": command_type,
                    "result": result,
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as exc:
            logger.exception("Failed to handle IPC command: %s", command_type)
            await self.ipc.push_response(
                response_command_id,
                {
                    "type": "command_failed",
                    "ok": False,
                    "request_id": request_id,
                    "command_type": command_type,
                    "error": str(exc),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    async def _toggle_service(self, payload: dict) -> dict:
        service = payload.get("service")
        enabled = payload.get("enabled")
        if not isinstance(service, str) or not service.strip():
            raise ValueError("service must be a non-empty string")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be boolean")

        await RedisManager.hset(self.features_hash_key, service, enabled)
        return {"service": service, "enabled": enabled}

    async def _set_channel_config(self, payload: dict) -> dict:
        channel_key = payload.get("channel_key")
        channel_id = payload.get("channel_id")
        if not isinstance(channel_key, str) or not channel_key.strip():
            raise ValueError("channel_key must be a non-empty string")

        if channel_id is None:
            await RedisManager.hdel(self.channels_hash_key, channel_key)
            return {"channel_key": channel_key, "channel_id": None}

        if not isinstance(channel_id, int) or channel_id <= 0:
            raise ValueError("channel_id must be a positive integer or null")

        await RedisManager.hset(self.channels_hash_key, channel_key, channel_id)
        return {"channel_key": channel_key, "channel_id": channel_id}

    @staticmethod
    def _trigger_forum_sync() -> dict:
        # Legacy forum watch tasks were removed in favor of backend-owned ingestion flows.
        return {"queued_tasks": [], "note": "forum sync watchers deprecated"}

    @staticmethod
    def _trigger_cop_scores_refresh() -> dict:
        celery_app.send_task("bot.tasks.forum_tasks.fetch_cop_scores")
        return {"queued_tasks": ["fetch_cop_scores"]}

    async def _publish_activity_forum(self, payload: dict) -> dict:
        if self.bot is None or not hasattr(self.bot, "forum_service"):
            raise RuntimeError("Bot forum service is not initialized")

        topic_number = payload.get("forum_topic_id")
        activity_public_id = payload.get("activity_public_id")
        title = payload.get("title")
        activity_type = payload.get("activity_type")
        duration_minutes = payload.get("duration_minutes")
        scheduled_for = payload.get("scheduled_for")
        notes = payload.get("notes")

        if not isinstance(topic_number, str) or not topic_number.strip():
            raise ValueError("forum_topic_id is required for publish_activity_forum")
        if not isinstance(activity_public_id, str) or not activity_public_id.strip():
            raise ValueError("activity_public_id is required")

        message_lines = [
            f"[b]{title or 'Group Activity'}[/b]",
            f"Activity ID: {activity_public_id}",
            f"Type: {activity_type or 'unknown'}",
            f"Duration: {duration_minutes or 'unknown'} minutes",
        ]
        if scheduled_for:
            message_lines.append(f"Scheduled For: {scheduled_for}")
        if notes:
            message_lines.append(f"Notes: {notes}")
        message_text = "\n".join(message_lines)

        result = await self.bot.forum_service.send_message_with_result(
            topic_number=topic_number.strip(),
            message_text=message_text,
            thread_id=f"activity:{activity_public_id}",
        )
        return {
            "success": bool(result.get("success")),
            "topic_number": str(result.get("topic_number") or topic_number).strip(),
            "post_id": result.get("post_id"),
            "error": result.get("error"),
        }
