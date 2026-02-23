from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class VacationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leave_date: date
    expected_return_date: date
    target_group: str | None = Field(default=None, max_length=255)
    reason: str | None = None


class VacationReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_comment: str | None = None


class VacationResponse(BaseModel):
    public_id: str
    player_id: int
    requester_user_id: int
    leave_date: date
    expected_return_date: date
    target_group: str | None = None
    status: str
    reason: str | None = None
    review_comment: str | None = None
    reviewed_by_user_id: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class VacationPoliciesResponse(BaseModel):
    max_duration_days: int
