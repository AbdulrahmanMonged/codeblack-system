from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: int
    discord_user_id: int
    username: str
    role_ids: tuple[int, ...]
    permissions: tuple[str, ...]
    is_owner: bool
    is_verified: bool = False
    account_name: str | None = None
    avatar_url: str | None = None
    token_jti: str | None = None


@dataclass(frozen=True)
class IssuedAccessToken:
    access_token: str
    expires_at: datetime
    token_jti: str
