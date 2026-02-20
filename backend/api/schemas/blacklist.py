from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BlacklistCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: int | None = None
    blacklist_level: int = Field(default=1, ge=1, le=99)
    alias: str = Field(min_length=2, max_length=255)
    identity: str = Field(min_length=2, max_length=255)
    serial: str | None = Field(default=None, max_length=64)
    roots: str | None = Field(default=None, min_length=2, max_length=2)
    remarks: str = Field(min_length=3)


class BlacklistUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blacklist_level: int | None = Field(default=None, ge=1, le=99)
    alias: str | None = Field(default=None, max_length=255)
    serial: str | None = Field(default=None, max_length=64)
    roots: str | None = Field(default=None, min_length=2, max_length=2)
    remarks: str | None = None


class BlacklistRemoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class BlacklistEntryResponse(BaseModel):
    id: int
    blacklist_player_id: str
    blacklist_sequence: int
    suffix_key: str
    player_id: int | None = None
    blacklist_level: int
    alias: str
    identity: str
    serial: str | None = None
    roots: str | None = None
    remarks: str
    status: str
    created_by_user_id: int
    removed_by_user_id: int | None = None
    created_at: datetime
    removed_at: datetime | None = None


class BlacklistRemovalRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_name: str = Field(min_length=2, max_length=255)
    request_text: str = Field(min_length=3)


class BlacklistRemovalRequestResponse(BaseModel):
    id: int
    public_id: str
    blacklist_entry_id: int | None = None
    account_name: str
    request_text: str
    status: str
    review_comment: str | None = None
    requested_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by_user_id: int | None = None


class BlacklistRemovalReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_comment: str | None = None


class BlacklistRemovalCheckResponse(BaseModel):
    class RecentRemovalRequest(BaseModel):
        public_id: str
        status: str
        requested_at: datetime
        reviewed_at: datetime | None = None
        review_comment: str | None = None

    account_name: str
    is_blacklisted: bool
    blacklist_entry_id: int | None = None
    blacklist_player_id: str | None = None
    blacklist_level: int | None = None
    status: str | None = None
    status_message: str | None = None
    can_submit: bool = False
    pending_request_public_id: str | None = None
    recent_requests: list[RecentRemovalRequest] = Field(default_factory=list)
