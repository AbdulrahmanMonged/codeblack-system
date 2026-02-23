from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RankCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=255)
    level: int = Field(ge=1, le=1000)


class RankResponse(BaseModel):
    id: int
    name: str
    level: int
    is_active: bool


class PlayerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingame_name: str = Field(min_length=2, max_length=255)
    account_name: str = Field(min_length=2, max_length=255)
    mta_serial: str | None = Field(default=None, max_length=64)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)


class PlayerResponse(BaseModel):
    id: int
    public_player_id: str | None = None
    ingame_name: str
    account_name: str
    mta_serial: str | None = None
    country_code: str | None = None
    created_at: datetime
    updated_at: datetime


class MembershipCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: int
    status: str = "active"
    joined_at: date | None = None
    current_rank_id: int | None = None
    display_rank: str | None = None
    is_on_leave: bool = False
    notes: str | None = None


class MembershipUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    left_at: date | None = None
    current_rank_id: int | None = None
    display_rank: str | None = None
    is_on_leave: bool | None = None
    notes: str | None = None


class RosterMembershipResponse(BaseModel):
    membership_id: int
    player: dict
    status: str
    joined_at: date | None = None
    left_at: date | None = None
    current_rank_id: int | None = None
    display_rank: str | None = None
    is_on_leave: bool
    notes: str | None = None
    updated_at: datetime


class PunishmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    punishment_type: str = Field(min_length=2, max_length=32)
    severity: int = Field(ge=1, le=10)
    reason: str = Field(min_length=3)
    expires_at: datetime | None = None


class PunishmentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    expires_at: datetime | None = None


class PunishmentResponse(BaseModel):
    id: int
    player_id: int
    punishment_type: str
    severity: int
    reason: str
    issued_by_user_id: int
    issued_at: datetime
    expires_at: datetime | None = None
    status: str
