from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderResponse(BaseModel):
    public_id: str
    status: str
    submitted_at: datetime
    updated_at: datetime
    submitted_by_user_id: int
    discord_user_id: int
    ingame_name: str
    account_name: str
    completed_orders: str
    proof_file_key: str
    proof_file_url: str
    proof_content_type: str
    proof_size_bytes: int


class OrderDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(accepted|denied)$")
    reason: str | None = None


class AccountLinkUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discord_user_id: int
    account_name: str = Field(min_length=2, max_length=255)
    is_verified: bool = False


class AccountLinkResponse(BaseModel):
    user_id: int
    discord_user_id: int
    account_name: str
    is_verified: bool
    created_at: datetime
    updated_at: datetime
