from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChannelConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    live_scores_channel_id: int | None = None
    recruitment_review_channel_id: int | None = None
    orders_notification_channel_id: int | None = None
    error_report_channel_id: int | None = None


class FeatureConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    watch_cop_live_scores: bool | None = None
    irc_bridge: bool | None = None
    group_chat_watcher: bool | None = None
    activity_monitor: bool | None = None


class CommandDispatchResponse(BaseModel):
    command_id: str
    command_type: str
    acknowledged: bool
    response: dict[str, Any] | None = None
    attempts: int = 1
    attempt_command_ids: list[str] = Field(default_factory=list)
    dead_lettered: bool = False
    dead_letter_id: str | None = None
    error: str | None = None
    channel_key: str | None = None
    service: str | None = None
    enabled: bool | None = None


class ChannelConfigResponse(BaseModel):
    live_scores_channel_id: int | None = None
    recruitment_review_channel_id: int | None = None
    orders_notification_channel_id: int | None = None
    error_report_channel_id: int | None = None


class FeatureConfigResponse(BaseModel):
    watch_cop_live_scores: bool
    irc_bridge: bool
    group_chat_watcher: bool
    activity_monitor: bool


class BotControlUpdateResponse(BaseModel):
    config: dict[str, Any]
    dispatch_results: list[CommandDispatchResponse]


class DeadLetterEntryResponse(BaseModel):
    stream_id: str
    command_type: str
    actor_user_id: int | None = None
    attempt_count: int
    attempt_command_ids: list[str] = Field(default_factory=list)
    error: str | None = None
    failed_at: str | None = None
    original_payload: dict[str, Any] | None = None
    last_response: dict[str, Any] | None = None


class DeadLetterReplayResponse(BaseModel):
    dead_letter_id: str
    command_id: str
    command_type: str
    acknowledged: bool
    attempts: int
    attempt_command_ids: list[str] = Field(default_factory=list)
    dead_lettered: bool = False
    dead_letter_id_new: str | None = None
    replay_record_id: str | None = None
    response: dict[str, Any] | None = None
    error: str | None = None
