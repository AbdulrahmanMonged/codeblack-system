from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class VotingCountsResponse(BaseModel):
    yes: int
    no: int
    total: int


class VotingContextResponse(BaseModel):
    context_type: str
    context_id: str
    status: str
    opened_by_user_id: int | None = None
    closed_by_user_id: int | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    close_reason: str | None = None
    auto_close_at: datetime | None = None
    title: str | None = None
    metadata_json: dict[str, Any] | None = None
    counts: VotingCountsResponse
    my_vote: str | None = None


class VotingVoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice: Literal["yes", "no"]
    comment_text: str | None = Field(default=None, max_length=4000)


class VotingVoteResponse(VotingContextResponse):
    last_vote: dict[str, Any]


class VotingVoterResponse(BaseModel):
    user_id: int
    discord_user_id: int
    username: str
    avatar_url: str | None = None
    name_color_hex: str | None = None
    choice: str
    comment_text: str | None = None
    cast_at: datetime
    updated_at: datetime


class VotingVotersResponse(BaseModel):
    context_type: str
    context_id: str
    status: str
    opened_by_user_id: int | None = None
    closed_by_user_id: int | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    close_reason: str | None = None
    auto_close_at: datetime | None = None
    title: str | None = None
    metadata_json: dict[str, Any] | None = None
    counts: VotingCountsResponse
    voters: list[VotingVoterResponse]


class VotingModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=2000)


class VotingResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=2000)
    reopen: bool = True


class VotingStateTransitionResponse(VotingContextResponse):
    state_transition: dict[str, str]


class VotingResetResponse(VotingContextResponse):
    reset: dict[str, Any]
