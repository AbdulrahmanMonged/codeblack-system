from __future__ import annotations

from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Any

import jwt

from backend.core.config import BackendSettings
from backend.core.errors import ApiException


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def random_jti(length: int = 32) -> str:
    return token_urlsafe(length)


def create_signed_token(
    *,
    settings: BackendSettings,
    token_type: str,
    claims: dict[str, Any],
    ttl_seconds: int,
) -> tuple[str, datetime]:
    issued_at = utc_now()
    expires_at = issued_at + timedelta(seconds=ttl_seconds)
    payload = {
        **claims,
        "type": token_type,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def decode_signed_token(
    *,
    settings: BackendSettings,
    token: str,
    expected_type: str,
) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            leeway=settings.JWT_LEEWAY_SECONDS,
        )
    except jwt.ExpiredSignatureError as exc:
        raise ApiException(
            status_code=401,
            error_code="TOKEN_EXPIRED",
            message="Authentication token expired",
        ) from exc
    except jwt.PyJWTError as exc:
        raise ApiException(
            status_code=401,
            error_code="TOKEN_INVALID",
            message="Authentication token invalid",
        ) from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise ApiException(
            status_code=401,
            error_code="TOKEN_TYPE_INVALID",
            message="Token type is invalid",
        )
    return payload
