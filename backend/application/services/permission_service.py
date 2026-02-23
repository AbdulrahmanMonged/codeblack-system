from __future__ import annotations

from backend.core.config import get_settings
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.auth_repository import AuthRepository


class PermissionService:
    def __init__(self):
        self.settings = get_settings()

    async def list_role_matrix(
        self,
        *,
        limit: int,
        offset: int,
        sync_roles: bool = False,
    ) -> list[dict]:
        if sync_roles:
            from backend.application.services.auth_service import AuthService

            await AuthService().sync_discord_roles()

        async with get_session() as session:
            repo = AuthRepository(session)
            roles = await repo.list_discord_roles(guild_id=self.settings.DISCORD_GUILD_ID)
            role_permission_pairs = await repo.list_role_permission_pairs()

        permission_map: dict[int, set[str]] = {}
        for role_id, permission_key in role_permission_pairs:
            permission_map.setdefault(role_id, set()).add(permission_key)

        result: list[dict] = []
        page_offset = max(0, int(offset))
        page_limit = max(1, int(limit))
        paged_roles = roles[page_offset : page_offset + page_limit]
        for role in paged_roles:
            assigned = sorted(permission_map.get(role.discord_role_id, set()))
            result.append(
                {
                    "discord_role_id": str(role.discord_role_id),
                    "guild_id": str(role.guild_id),
                    "name": role.name,
                    "position": role.position,
                    "is_active": role.is_active,
                    "assigned_permissions": assigned,
                }
            )
        return result

    async def list_permission_catalog(self) -> list[str]:
        async with get_session() as session:
            repo = AuthRepository(session)
            permissions = await repo.list_permissions()
        return sorted({permission.key for permission in permissions})

    async def update_role_permissions(
        self,
        *,
        discord_role_id: int,
        permission_keys: list[str],
    ) -> dict:
        normalized_keys = sorted(set(permission_keys))
        selected_role = None
        role_sync_attempted = False

        while True:
            async with get_session() as session:
                repo = AuthRepository(session)
                roles = await repo.list_discord_roles(guild_id=self.settings.DISCORD_GUILD_ID)
                selected_role = next(
                    (role for role in roles if role.discord_role_id == discord_role_id),
                    None,
                )

                if selected_role is not None:
                    existing_permission_keys = await repo.list_existing_permission_keys(normalized_keys)
                    missing = sorted(set(normalized_keys) - existing_permission_keys)
                    if missing:
                        raise ApiException(
                            status_code=422,
                            error_code="UNKNOWN_PERMISSION_KEYS",
                            message="One or more permission keys are unknown",
                            details={"unknown_permission_keys": missing},
                        )

                    await repo.replace_role_permissions(
                        discord_role_id=discord_role_id,
                        permission_keys=normalized_keys,
                    )
                    break

            if role_sync_attempted:
                raise ApiException(
                    status_code=404,
                    error_code="DISCORD_ROLE_NOT_FOUND",
                    message=f"Discord role {discord_role_id} not found in cache",
                )

            role_sync_attempted = True
            from backend.application.services.auth_service import AuthService

            try:
                await AuthService().sync_discord_roles()
            except ApiException as exc:
                raise ApiException(
                    status_code=404,
                    error_code="DISCORD_ROLE_NOT_FOUND",
                    message=f"Discord role {discord_role_id} not found in cache",
                    details={"role_sync_error": exc.error_code},
                ) from exc

        return {
            "discord_role_id": str(selected_role.discord_role_id),
            "guild_id": str(selected_role.guild_id),
            "name": selected_role.name,
            "position": selected_role.position,
            "is_active": selected_role.is_active,
            "assigned_permissions": normalized_keys,
        }
