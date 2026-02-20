from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, Response

from backend.api.deps.auth import get_current_principal, get_optional_principal
from backend.api.schemas.auth import AuthLoginResponse, AuthSessionResponse, AuthUserResponse
from backend.api.schemas.common import OperationResponse
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.auth_service import AuthService
from backend.core.config import BackendSettings

router = APIRouter()


def get_auth_service() -> AuthService:
    return AuthService()


def _to_auth_user(principal: AuthenticatedPrincipal) -> AuthUserResponse:
    return AuthUserResponse(
        user_id=principal.user_id,
        discord_user_id=str(principal.discord_user_id),
        username=principal.username,
        role_ids=[str(role_id) for role_id in principal.role_ids],
        permissions=list(principal.permissions),
        is_owner=principal.is_owner,
        is_verified=principal.is_verified,
        account_name=principal.account_name,
        avatar_url=principal.avatar_url,
    )


def _set_auth_cookie(
    response: Response,
    *,
    settings: BackendSettings,
    token: str,
    expires_at: datetime,
) -> None:
    expires_in_seconds = max(
        0,
        int((expires_at - datetime.now(timezone.utc)).total_seconds()),
    )
    max_age = min(settings.auth_cookie_max_age_seconds, expires_in_seconds) if expires_in_seconds else 0
    response.set_cookie(
        key=settings.BACKEND_AUTH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=max_age,
        path=settings.BACKEND_AUTH_COOKIE_PATH or "/",
        domain=settings.auth_cookie_domain,
        secure=settings.BACKEND_AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


def _clear_auth_cookie(
    response: Response,
    *,
    settings: BackendSettings,
) -> None:
    response.delete_cookie(
        key=settings.BACKEND_AUTH_COOKIE_NAME,
        path=settings.BACKEND_AUTH_COOKIE_PATH or "/",
        domain=settings.auth_cookie_domain,
        secure=settings.BACKEND_AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


@router.get("/discord/login", response_model=AuthLoginResponse)
async def discord_login(
    next_url: str | None = Query(default=None, max_length=2048),
    service: AuthService = Depends(get_auth_service),
):
    payload = await service.build_discord_login(next_url=next_url)
    return AuthLoginResponse(**payload)


@router.get("/discord/callback", response_model=AuthSessionResponse)
async def discord_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    issued, principal = await service.exchange_discord_callback(
        code=code,
        state=state,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    _set_auth_cookie(
        response,
        settings=service.settings,
        token=issued.access_token,
        expires_at=issued.expires_at,
    )
    return AuthSessionResponse(
        expires_at=issued.expires_at,
        user=_to_auth_user(principal),
    )


@router.get("/me", response_model=AuthUserResponse)
async def auth_me(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
):
    return _to_auth_user(principal)


@router.post("/logout", response_model=OperationResponse)
async def auth_logout(
    response: Response,
    principal: AuthenticatedPrincipal | None = Depends(get_optional_principal),
    service: AuthService = Depends(get_auth_service),
):
    if principal is not None and principal.token_jti:
        await service.logout(principal.token_jti)
    _clear_auth_cookie(response, settings=service.settings)
    return OperationResponse(ok=True, message="Logged out")
