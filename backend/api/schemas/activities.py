from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActivityCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_type: str = Field(min_length=2, max_length=32)
    title: str = Field(min_length=2, max_length=255)
    duration_minutes: int = Field(ge=1, le=24 * 60)
    notes: str | None = None
    scheduled_for: datetime | None = None


class ActivityReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_comment: str | None = None
    scheduled_for: datetime | None = None


class ActivityPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forum_topic_id: str | None = Field(default=None, min_length=1, max_length=255)
    force_retry: bool = False


class ActivityParticipantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: int
    participant_role: str = "participant"
    attendance_status: str = "planned"
    notes: str | None = None


class ActivityParticipantResponse(BaseModel):
    id: int
    player_id: int
    participant_role: str
    attendance_status: str
    notes: str | None = None


class ActivityResponse(BaseModel):
    public_id: str
    activity_type: str
    title: str
    duration_minutes: int
    notes: str | None = None
    status: str
    created_by_user_id: int
    approved_by_user_id: int | None = None
    approval_comment: str | None = None
    scheduled_for: datetime | None = None
    forum_topic_id: str | None = None
    forum_post_id: str | None = None
    publish_attempts: int
    last_publish_error: str | None = None
    last_publish_attempt_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    participants: list[ActivityParticipantResponse]


class ActivityPublishResponse(BaseModel):
    activity: ActivityResponse
    dispatch: dict[str, Any]
