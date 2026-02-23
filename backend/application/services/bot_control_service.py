from __future__ import annotations

from typing import Any

from backend.core.config import get_settings
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.domain.policies.bot_control_guardrails import BotControlGuardrails
from backend.infrastructure.ipc.stream_client import BackendIPCClient
from backend.infrastructure.repositories.config_registry_repository import (
    ConfigRegistryRepository,
)


class BotControlService:
    CHANNELS_CONFIG_KEY = "bot.channels"
    FEATURES_CONFIG_KEY = "bot.features"

    def __init__(self):
        self.settings = get_settings()

    @property
    def channel_defaults(self) -> dict[str, int | None]:
        return {key: None for key in BotControlGuardrails.CHANNEL_KEYS}

    @property
    def feature_defaults(self) -> dict[str, bool]:
        return {key: True for key in BotControlGuardrails.FEATURE_KEYS}

    async def get_channels(self) -> dict[str, int | None]:
        return await self._get_config_entry(
            key=self.CHANNELS_CONFIG_KEY,
            defaults=self.channel_defaults,
        )

    async def get_features(self) -> dict[str, bool]:
        return await self._get_config_entry(
            key=self.FEATURES_CONFIG_KEY,
            defaults=self.feature_defaults,
        )

    async def update_channels(
        self,
        *,
        payload: dict[str, int | None],
        actor_user_id: int,
    ) -> dict[str, Any]:
        issues = BotControlGuardrails.validate_channels(payload)
        if issues:
            raise ApiException(
                status_code=422,
                error_code="INVALID_CHANNEL_CONFIG",
                message="Channel configuration payload is invalid",
                details={"issues": issues},
            )

        current = await self.get_channels()
        merged = {**current, **payload}
        changed_items = {
            key: value for key, value in merged.items() if current.get(key) != value
        }
        if not changed_items:
            return {"config": current, "dispatch_results": []}

        async with get_session() as session:
            repo = ConfigRegistryRepository(session)
            await repo.upsert(
                key=self.CHANNELS_CONFIG_KEY,
                value_json=merged,
                schema_version=1,
                is_sensitive=False,
                updated_by_user_id=actor_user_id,
            )
            await repo.add_change(
                config_key=self.CHANNELS_CONFIG_KEY,
                before_json=current,
                after_json=merged,
                schema_version=1,
                is_sensitive=False,
                changed_by_user_id=actor_user_id,
                change_reason="Updated bot channel routing",
                requires_approval=False,
                status="applied",
            )

        command_results = await self._dispatch_channel_commands(
            actor_user_id=actor_user_id,
            changed_items=changed_items,
        )
        return {
            "config": merged,
            "dispatch_results": command_results,
        }

    async def update_features(
        self,
        *,
        payload: dict[str, bool],
        actor_user_id: int,
    ) -> dict[str, Any]:
        issues = BotControlGuardrails.validate_features(payload)
        if issues:
            raise ApiException(
                status_code=422,
                error_code="INVALID_FEATURE_CONFIG",
                message="Feature toggle payload is invalid",
                details={"issues": issues},
            )

        current = await self.get_features()
        merged = {**current, **payload}
        changed_items = {
            key: value for key, value in merged.items() if current.get(key) != value
        }
        if not changed_items:
            return {"config": current, "dispatch_results": []}

        async with get_session() as session:
            repo = ConfigRegistryRepository(session)
            await repo.upsert(
                key=self.FEATURES_CONFIG_KEY,
                value_json=merged,
                schema_version=1,
                is_sensitive=False,
                updated_by_user_id=actor_user_id,
            )
            await repo.add_change(
                config_key=self.FEATURES_CONFIG_KEY,
                before_json=current,
                after_json=merged,
                schema_version=1,
                is_sensitive=False,
                changed_by_user_id=actor_user_id,
                change_reason="Updated bot feature toggles",
                requires_approval=False,
                status="applied",
            )

        command_results = await self._dispatch_feature_commands(
            actor_user_id=actor_user_id,
            changed_items=changed_items,
        )
        return {
            "config": merged,
            "dispatch_results": command_results,
        }

    async def trigger_forum_sync(self, *, actor_user_id: int) -> dict[str, Any]:
        return await self._dispatch_single_command(
            command_type="trigger_forum_sync",
            actor_user_id=actor_user_id,
            payload={},
        )

    async def trigger_cop_scores_refresh(self, *, actor_user_id: int) -> dict[str, Any]:
        return await self._dispatch_single_command(
            command_type="trigger_cop_scores_refresh",
            actor_user_id=actor_user_id,
            payload={},
        )

    async def list_dead_letters(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        ipc = BackendIPCClient()
        try:
            return await ipc.list_dead_letters(limit=limit, offset=offset)
        finally:
            await ipc.close()

    async def replay_dead_letter(
        self,
        *,
        dead_letter_id: str,
        actor_user_id: int,
    ) -> dict[str, Any]:
        ipc = BackendIPCClient()
        try:
            replay = await ipc.replay_dead_letter(
                dead_letter_id=dead_letter_id,
                actor_user_id=actor_user_id,
                timeout_seconds=self.settings.BOT_COMMAND_ACK_TIMEOUT_SECONDS,
            )
            return replay
        finally:
            await ipc.close()

    async def _get_config_entry(self, *, key: str, defaults: dict) -> dict:
        async with get_session() as session:
            repo = ConfigRegistryRepository(session)
            entry = await repo.get_by_key(key)
        if entry is None or not isinstance(entry.value_json, dict):
            return defaults
        return {**defaults, **entry.value_json}

    async def _dispatch_channel_commands(
        self,
        *,
        actor_user_id: int,
        changed_items: dict[str, int | None],
    ) -> list[dict]:
        ipc = BackendIPCClient()
        results: list[dict] = []
        try:
            for channel_key, channel_id in changed_items.items():
                dispatch = await ipc.dispatch_command_with_retry(
                    command_type="set_channel_config",
                    actor_user_id=actor_user_id,
                    payload={
                        "channel_key": channel_key,
                        "channel_id": channel_id,
                    },
                    timeout_seconds=self.settings.BOT_COMMAND_ACK_TIMEOUT_SECONDS,
                )
                results.append(
                    {
                        "command_type": "set_channel_config",
                        "channel_key": channel_key,
                        **dispatch,
                    }
                )
        finally:
            await ipc.close()
        return results

    async def _dispatch_feature_commands(
        self,
        *,
        actor_user_id: int,
        changed_items: dict[str, bool],
    ) -> list[dict]:
        ipc = BackendIPCClient()
        results: list[dict] = []
        try:
            for service_name, enabled in changed_items.items():
                dispatch = await ipc.dispatch_command_with_retry(
                    command_type="toggle_service",
                    actor_user_id=actor_user_id,
                    payload={
                        "service": service_name,
                        "enabled": enabled,
                    },
                    timeout_seconds=self.settings.BOT_COMMAND_ACK_TIMEOUT_SECONDS,
                )
                results.append(
                    {
                        "command_type": "toggle_service",
                        "service": service_name,
                        "enabled": enabled,
                        **dispatch,
                    }
                )
        finally:
            await ipc.close()
        return results

    async def _dispatch_single_command(
        self,
        *,
        command_type: str,
        actor_user_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        ipc = BackendIPCClient()
        try:
            dispatch = await ipc.dispatch_command_with_retry(
                command_type=command_type,
                actor_user_id=actor_user_id,
                payload=payload,
                timeout_seconds=self.settings.BOT_COMMAND_ACK_TIMEOUT_SECONDS,
            )
            return {
                "command_type": command_type,
                **dispatch,
            }
        finally:
            await ipc.close()
