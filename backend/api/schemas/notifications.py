from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    public_id: str
    event_type: str
    category: str
    severity: str
    title: str
    body: str
    entity_type: str | None = None
    entity_public_id: str | None = None
    actor_user_id: int | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    is_read: bool
    read_at: datetime | None = None


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationMarkAllReadResponse(BaseModel):
    updated_count: int


class NotificationDeleteResponse(BaseModel):
    deleted_count: int


class NotificationBroadcastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=2, max_length=128)
    category: str = Field(min_length=2, max_length=64)
    severity: Literal["info", "success", "warning", "critical"] = "info"
    title: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=2)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_public_id: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] | None = None


class NotificationBroadcastResponse(BaseModel):
    public_id: str
    event_type: str
    category: str
    severity: str
    title: str
    body: str
    entity_type: str | None = None
    entity_public_id: str | None = None
    actor_user_id: int | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    recipient_count: int


class NotificationTargetedSendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=2, max_length=128)
    category: str = Field(min_length=2, max_length=64)
    severity: Literal["info", "success", "warning", "critical"] = "info"
    title: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=2)
    user_ids: list[int] = Field(default_factory=list)
    role_ids: list[int] = Field(default_factory=list)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_public_id: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] | None = None


class NotificationTargetedSendResponse(NotificationBroadcastResponse):
    recipient_user_ids: list[int] = Field(default_factory=list)
