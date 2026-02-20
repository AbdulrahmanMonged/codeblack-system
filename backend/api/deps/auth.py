from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.auth_service import AuthService
from backend.core.config import get_settings
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.auth_repository import AuthRepository
from backend.infrastructure.repositories.blacklist_repository import BlacklistRepository
from backend.infrastructure.repositories.order_repository import OrderRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_optional_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedPrincipal | None:
    if credentials is None:
        return None
    token = credentials.credentials
    if not token:
        return None
    service = AuthService()
    principal = await service.get_principal_from_access_token(token)
    request.state.authenticated_principal = principal
    return principal


async def get_current_principal(
    request: Request,
    principal: AuthenticatedPrincipal | None = Depends(get_optional_principal),
) -> AuthenticatedPrincipal:
    if principal is None and get_settings().dev_unlock_enabled:
        principal = await _get_or_create_dev_principal()

    if principal is None:
        raise ApiException(
            status_code=401,
            error_code="AUTH_REQUIRED",
            message="Authentication is required for this endpoint",
        )
    request.state.authenticated_principal = principal
    return principal


def require_permissions(*permission_keys: str) -> Callable[[AuthenticatedPrincipal], AuthenticatedPrincipal]:
    required = tuple(key for key in permission_keys if key)

    async def _dependency(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> AuthenticatedPrincipal:
        if get_settings().dev_unlock_enabled:
            return principal

        if principal.is_owner:
            return principal

        if "blacklist_removal_requests.create" not in required:
            if await _is_principal_blacklisted(principal):
                raise ApiException(
                    status_code=403,
                    error_code="BLACKLIST_ACTIVE",
                    message="Restricted action denied due to active blacklist status",
                )

        missing = [key for key in required if key not in principal.permissions]
        if missing:
            raise ApiException(
                status_code=403,
                error_code="PERMISSION_DENIED",
                message="You do not have required permissions",
                details={"missing_permissions": missing},
            )
        return principal

    return _dependency


def require_any_permissions(
    *permission_keys: str,
) -> Callable[[AuthenticatedPrincipal], AuthenticatedPrincipal]:
    required = tuple(key for key in permission_keys if key)

    async def _dependency(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> AuthenticatedPrincipal:
        if principal.is_owner:
            return principal

        if required and not set(required).intersection(VERIFICATION_BYPASS_PERMISSION_KEYS):
            if not principal.is_verified:
                raise ApiException(
                    status_code=403,
                    error_code="VERIFICATION_REQUIRED",
                    message="Account verification is required for this action",
                )

        if "blacklist_removal_requests.create" not in required:
            if await _is_principal_blacklisted(principal):
                raise ApiException(
                    status_code=403,
                    error_code="BLACKLIST_ACTIVE",
                    message="Restricted action denied due to active blacklist status",
                )

        if required and not any(key in principal.permissions for key in required):
            raise ApiException(
                status_code=403,
                error_code="PERMISSION_DENIED",
                message="You do not have required permissions",
                details={"required_any_permissions": list(required)},
            )
        return principal

    return _dependency


async def _get_or_create_dev_principal() -> AuthenticatedPrincipal:
    settings = get_settings()
    owner_ids = sorted(settings.owner_discord_ids)
    default_owner_discord_id = owner_ids[0] if owner_ids else 757387358621532164

    async with get_session() as session:
        repo = AuthRepository(session)
        user = None
        for owner_discord_id in owner_ids:
            user = await repo.get_user_by_discord_id(owner_discord_id)
            if user is not None:
                break

        if user is None:
            user = await repo.upsert_user(
                discord_user_id=default_owner_discord_id,
                username="Dev Owner",
                avatar_hash=None,
            )

        await repo.set_user_permission(
            user_id=user.id,
            permission_key="owner.override",
            allow=True,
        )
        permissions = await repo.list_effective_permission_keys(user.id)
        role_ids = await repo.list_user_role_ids(user.id)

    return AuthenticatedPrincipal(
        user_id=user.id,
        discord_user_id=default_owner_discord_id,
        username=user.username,
        role_ids=tuple(sorted(role_ids)),
        permissions=tuple(sorted(permissions)),
        is_owner=True,
        token_jti=None,
    )


async def _is_principal_blacklisted(principal: AuthenticatedPrincipal) -> bool:
    async with get_session() as session:
        order_repo = OrderRepository(session)
        blacklist_repo = BlacklistRepository(session)
        link = await order_repo.get_user_game_account_by_discord(principal.discord_user_id)
        if link is None:
            return False
        entry = await blacklist_repo.find_active_by_account_name(link.account_name)
        return entry is not None
