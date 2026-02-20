from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VerificationRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_name: str = Field(min_length=2, max_length=255)
    mta_serial: str = Field(min_length=10, max_length=64)
    forum_url: str = Field(min_length=3, max_length=1024)


class VerificationReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_comment: str | None = Field(default=None, max_length=4000)


class VerificationRequestResponse(BaseModel):
    public_id: str
    user_id: int
    discord_user_id: int
    account_name: str
    mta_serial: str
    forum_url: str
    status: str
    review_comment: str | None = None
    reviewed_by_user_id: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
