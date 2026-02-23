from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from redis.asyncio import Redis

from backend.core.config import get_settings
from backend.core.metrics import metrics_registry

logger = logging.getLogger(__name__)


class BackendIPCClient:
    def __init__(self):
        self.settings = get_settings()
        self._redis: Redis | None = None
        prefix = self.settings.IPC_STREAM_PREFIX
        self.commands_stream = f"{prefix}:stream:commands"
        self.responses_stream = f"{prefix}:stream:responses"
        self.dead_letter_stream = f"{prefix}:stream:commands:dlq"
        self.dead_letter_replay_stream = f"{prefix}:stream:commands:dlq:replay"

    async def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def push_command(
        self,
        *,
        command_type: str,
        actor_user_id: int,
        payload: dict,
    ) -> tuple[str, str]:
        redis = await self._client()
        latest = await redis.xrevrange(self.responses_stream, count=1)
        response_cursor = latest[0][0] if latest else "0-0"

        request_id = str(uuid4())
        message = {
            "type": command_type,
            "request_id": request_id,
            "actor_user_id": actor_user_id,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        serialized = {key: json.dumps(value) for key, value in message.items()}
        await redis.xadd(self.commands_stream, serialized, maxlen=10000, approximate=True)
        return request_id, response_cursor

    async def dispatch_command_with_retry(
        self,
        *,
        command_type: str,
        actor_user_id: int,
        payload: dict,
        timeout_seconds: int,
        max_retries: int | None = None,
        retry_backoff_ms: int | None = None,
    ) -> dict:
        retries = max_retries
        if retries is None:
            retries = max(0, int(self.settings.BACKEND_IPC_MAX_RETRIES))
        retries = max(0, retries)

        backoff_ms = retry_backoff_ms
        if backoff_ms is None:
            backoff_ms = max(50, int(self.settings.BACKEND_IPC_RETRY_BACKOFF_MS))
        backoff_ms = max(50, backoff_ms)
        started = perf_counter()

        issued_ids: list[str] = []
        last_response: dict | None = None
        last_error = "timeout"
        total_attempts = retries + 1

        for attempt in range(1, total_attempts + 1):
            command_id, response_cursor = await self.push_command(
                command_type=command_type,
                actor_user_id=actor_user_id,
                payload=payload,
            )
            issued_ids.append(command_id)
            response = await self.wait_for_response(
                command_id=command_id,
                response_cursor=response_cursor,
                timeout_seconds=timeout_seconds,
            )
            if response is not None and response.get("ok") is True:
                metrics_registry.record_ipc_command(
                    command_type=command_type,
                    result="ack",
                )
                metrics_registry.record_ipc_duration(
                    command_type=command_type,
                    duration_seconds=max(0.0, perf_counter() - started),
                )
                return {
                    "command_id": issued_ids[0],
                    "attempt_command_ids": issued_ids,
                    "attempts": attempt,
                    "acknowledged": True,
                    "response": response,
                    "dead_lettered": False,
                    "dead_letter_id": None,
                }

            if response is None:
                last_error = "timeout"
                metrics_registry.record_ipc_command(
                    command_type=command_type,
                    result="timeout",
                )
            else:
                last_response = response
                last_error = str(
                    response.get("error")
                    or response.get("message")
                    or response.get("type")
                    or "command_failed"
                )
                metrics_registry.record_ipc_command(
                    command_type=command_type,
                    result="command_failed",
                )

            if attempt <= retries:
                metrics_registry.record_ipc_retry(command_type=command_type)
                sleep_seconds = (backoff_ms * attempt) / 1000.0
                await asyncio.sleep(sleep_seconds)

        dead_letter_id = await self._push_dead_letter(
            command_type=command_type,
            actor_user_id=actor_user_id,
            payload=payload,
            attempt_command_ids=issued_ids,
            error=last_error,
            last_response=last_response,
        )
        metrics_registry.record_ipc_command(
            command_type=command_type,
            result="dead_lettered",
        )
        metrics_registry.record_ipc_duration(
            command_type=command_type,
            duration_seconds=max(0.0, perf_counter() - started),
        )
        return {
            "command_id": issued_ids[0] if issued_ids else "",
            "attempt_command_ids": issued_ids,
            "attempts": total_attempts,
            "acknowledged": False,
            "response": last_response,
            "dead_lettered": dead_letter_id is not None,
            "dead_letter_id": dead_letter_id,
            "error": last_error,
        }

    async def list_dead_letters(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        redis = await self._client()
        page_limit = max(1, int(limit))
        page_offset = max(0, int(offset))
        fetch_count = max(1, page_limit + page_offset)
        entries = await redis.xrevrange(self.dead_letter_stream, count=fetch_count)
        paged_entries = entries[page_offset : page_offset + page_limit]
        rows: list[dict] = []
        for stream_id, fields in paged_entries:
            decoded = self._decode_fields(fields)
            rows.append(
                {
                    "stream_id": stream_id,
                    "command_type": str(decoded.get("type") or ""),
                    "actor_user_id": _to_int_or_none(decoded.get("actor_user_id")),
                    "attempt_count": _to_int_or_default(
                        decoded.get("attempt_count"),
                        default=len(decoded.get("attempt_command_ids") or []),
                    ),
                    "attempt_command_ids": _to_list(decoded.get("attempt_command_ids")),
                    "error": _to_str_or_none(decoded.get("error")),
                    "failed_at": _to_str_or_none(decoded.get("failed_at")),
                    "original_payload": _to_dict_or_none(decoded.get("original_payload")),
                    "last_response": _to_dict_or_none(decoded.get("last_response")),
                }
            )
        return rows

    async def replay_dead_letter(
        self,
        *,
        dead_letter_id: str,
        actor_user_id: int,
        timeout_seconds: int,
    ) -> dict:
        row = await self.get_dead_letter_by_id(dead_letter_id)
        if row is None:
            return {
                "dead_letter_id": dead_letter_id,
                "command_id": "",
                "command_type": "",
                "acknowledged": False,
                "attempts": 0,
                "attempt_command_ids": [],
                "dead_lettered": False,
                "dead_letter_id_new": None,
                "response": None,
                "error": "dead_letter_not_found",
            }

        command_type = row.get("command_type") or ""
        original_payload = row.get("original_payload") or {}
        if not isinstance(original_payload, dict):
            original_payload = {}

        dispatch = await self.dispatch_command_with_retry(
            command_type=command_type,
            actor_user_id=actor_user_id,
            payload=original_payload,
            timeout_seconds=timeout_seconds,
        )
        replay_record_id = await self._push_dead_letter_replay_record(
            dead_letter_id=dead_letter_id,
            actor_user_id=actor_user_id,
            command_type=command_type,
            replay_result=dispatch,
        )
        return {
            "dead_letter_id": dead_letter_id,
            "command_id": dispatch.get("command_id", ""),
            "command_type": command_type,
            "acknowledged": bool(dispatch.get("acknowledged")),
            "attempts": int(dispatch.get("attempts", 0)),
            "attempt_command_ids": list(dispatch.get("attempt_command_ids") or []),
            "dead_lettered": bool(dispatch.get("dead_lettered")),
            "dead_letter_id_new": dispatch.get("dead_letter_id"),
            "response": dispatch.get("response"),
            "error": dispatch.get("error"),
            "replay_record_id": replay_record_id,
        }

    async def wait_for_response(
        self,
        *,
        command_id: str,
        response_cursor: str,
        timeout_seconds: int,
    ) -> dict | None:
        redis = await self._client()
        last_seen_id = response_cursor or "0-0"
        remaining_ms = max(1, int(timeout_seconds * 1000))

        while remaining_ms > 0:
            started_ms = datetime.now(timezone.utc).timestamp() * 1000
            messages = await redis.xread(
                {self.responses_stream: last_seen_id},
                count=20,
                block=remaining_ms,
            )
            elapsed_ms = int(datetime.now(timezone.utc).timestamp() * 1000 - started_ms)
            remaining_ms -= max(1, elapsed_ms)
            if not messages:
                continue

            for _, entries in messages:
                for entry_id, fields in entries:
                    last_seen_id = entry_id
                    decoded: dict = {}
                    for key, raw_value in fields.items():
                        try:
                            decoded[key] = json.loads(raw_value)
                        except (json.JSONDecodeError, TypeError):
                            decoded[key] = raw_value
                    if decoded.get("command_id") == command_id:
                        return decoded

        logger.warning("IPC command %s timed out waiting for bot response", command_id)
        return None

    async def get_dead_letter_by_id(self, dead_letter_id: str) -> dict | None:
        redis = await self._client()
        entries = await redis.xrange(
            self.dead_letter_stream,
            min=dead_letter_id,
            max=dead_letter_id,
            count=1,
        )
        if not entries:
            return None
        stream_id, fields = entries[0]
        decoded = self._decode_fields(fields)
        return {
            "stream_id": stream_id,
            "command_type": str(decoded.get("type") or ""),
            "actor_user_id": _to_int_or_none(decoded.get("actor_user_id")),
            "attempt_count": _to_int_or_default(
                decoded.get("attempt_count"),
                default=len(decoded.get("attempt_command_ids") or []),
            ),
            "attempt_command_ids": _to_list(decoded.get("attempt_command_ids")),
            "error": _to_str_or_none(decoded.get("error")),
            "failed_at": _to_str_or_none(decoded.get("failed_at")),
            "original_payload": _to_dict_or_none(decoded.get("original_payload")),
            "last_response": _to_dict_or_none(decoded.get("last_response")),
        }

    async def _push_dead_letter(
        self,
        *,
        command_type: str,
        actor_user_id: int,
        payload: dict,
        attempt_command_ids: list[str],
        error: str,
        last_response: dict | None,
    ) -> str | None:
        redis = await self._client()
        message = {
            "type": command_type,
            "actor_user_id": actor_user_id,
            "original_payload": payload,
            "attempt_command_ids": attempt_command_ids,
            "attempt_count": len(attempt_command_ids),
            "error": error,
            "last_response": last_response,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        serialized = {key: json.dumps(value) for key, value in message.items()}
        try:
            return await redis.xadd(
                self.dead_letter_stream,
                serialized,
                maxlen=max(1000, int(self.settings.BACKEND_IPC_DEAD_LETTER_MAXLEN)),
                approximate=True,
            )
        except Exception:
            logger.exception("Failed to write IPC dead-letter message for %s", command_type)
            return None

    async def _push_dead_letter_replay_record(
        self,
        *,
        dead_letter_id: str,
        actor_user_id: int,
        command_type: str,
        replay_result: dict,
    ) -> str | None:
        redis = await self._client()
        message = {
            "dead_letter_id": dead_letter_id,
            "actor_user_id": actor_user_id,
            "command_type": command_type,
            "replay_result": replay_result,
            "replayed_at": datetime.now(timezone.utc).isoformat(),
        }
        serialized = {key: json.dumps(value) for key, value in message.items()}
        try:
            return await redis.xadd(
                self.dead_letter_replay_stream,
                serialized,
                maxlen=max(1000, int(self.settings.BACKEND_IPC_DEAD_LETTER_MAXLEN)),
                approximate=True,
            )
        except Exception:
            logger.exception(
                "Failed to persist dead-letter replay record for %s", dead_letter_id
            )
            return None

    @staticmethod
    def _decode_fields(fields: dict) -> dict:
        decoded: dict = {}
        for key, raw_value in fields.items():
            try:
                decoded[key] = json.loads(raw_value)
            except (json.JSONDecodeError, TypeError):
                decoded[key] = raw_value
        return decoded


def _to_int_or_none(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_int_or_default(value, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_list(value) -> list:
    if isinstance(value, list):
        return value
    return []


def _to_dict_or_none(value) -> dict | None:
    if isinstance(value, dict):
        return value
    return None


def _to_str_or_none(value) -> str | None:
    if value is None:
        return None
    return str(value)
