from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps.auth import require_permissions
from backend.api.schemas.permissions import (
    RolePermissionMatrixItem,
    RolePermissionUpdateRequest,
)
from backend.application.services.permission_service import PermissionService

router = APIRouter()


def get_permission_service() -> PermissionService:
    return PermissionService()


@router.get("/role-matrix", response_model=list[RolePermissionMatrixItem])
async def list_role_matrix(
    _: object = Depends(require_permissions("discord_role_permissions.read")),
    service: PermissionService = Depends(get_permission_service),
):
    rows = await service.list_role_matrix()
    return [RolePermissionMatrixItem(**row) for row in rows]


@router.put("/role-matrix/{discord_role_id}", response_model=RolePermissionMatrixItem)
async def update_role_matrix(
    discord_role_id: int,
    payload: RolePermissionUpdateRequest,
    _: object = Depends(require_permissions("discord_role_permissions.write")),
    service: PermissionService = Depends(get_permission_service),
):
    row = await service.update_role_permissions(
        discord_role_id=discord_role_id,
        permission_keys=payload.permission_keys,
    )
    return RolePermissionMatrixItem(**row)
