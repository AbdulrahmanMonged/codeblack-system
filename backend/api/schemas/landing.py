from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class LandingPostResponse(BaseModel):
    public_id: str
    title: str
    content: str
    media_url: str | None = None
    is_published: bool
    published_at: datetime | None = None
    created_by_user_id: int | None = None
    updated_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime


class LandingPostCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=255)
    content: str = Field(min_length=2)
    media_url: str | None = Field(default=None, max_length=2048)


class LandingPostUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=2, max_length=255)
    content: str | None = Field(default=None, min_length=2)
    media_url: str | None = Field(default=None, max_length=2048)


class LandingPostPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_published: bool


class LandingPostMediaUploadResponse(BaseModel):
    media_url: str
    media_key: str
    content_type: str
    size_bytes: int


class PublicMetricsResponse(BaseModel):
    members_count: int
    current_level: str
    online_players: int


class PublicRosterEntryResponse(BaseModel):
    membership_id: int
    player_id: int
    public_player_id: str | None = None
    ingame_name: str
    account_name: str
    rank_name: str | None = None
    joined_at: date | None = None
    status: str
