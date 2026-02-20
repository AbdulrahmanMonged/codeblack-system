from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuthLoginResponse(BaseModel):
    authorize_url: str
    state: str
    state_expires_at: datetime
    next_url: str = ""


class AuthUserResponse(BaseModel):
    user_id: int
    discord_user_id: str
    username: str
    role_ids: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    is_owner: bool
    is_verified: bool = False
    account_name: str | None = None
    avatar_url: str | None = None


class AuthSessionResponse(BaseModel):
    expires_at: datetime
    user: AuthUserResponse


class DiscordRoleResponse(BaseModel):
    discord_role_id: int
    guild_id: int
    name: str
    position: int
    color_int: int
    is_active: bool
    synced_at: datetime
