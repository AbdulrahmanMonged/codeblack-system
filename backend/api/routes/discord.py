from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps.auth import require_permissions
from backend.api.schemas.auth import DiscordRoleResponse
from backend.application.services.auth_service import AuthService

router = APIRouter()


def get_auth_service() -> AuthService:
    return AuthService()


@router.get("/roles", response_model=list[DiscordRoleResponse])
async def list_discord_roles(
    _: object = Depends(require_permissions("discord_roles.read")),
    service: AuthService = Depends(get_auth_service),
):
    roles = await service.list_discord_roles()
    return [DiscordRoleResponse(**role) for role in roles]


@router.post("/roles/sync", response_model=list[DiscordRoleResponse])
async def sync_discord_roles(
    _: object = Depends(require_permissions("discord_roles.sync")),
    service: AuthService = Depends(get_auth_service),
):
    roles = await service.sync_discord_roles()
    return [DiscordRoleResponse(**role) for role in roles]
