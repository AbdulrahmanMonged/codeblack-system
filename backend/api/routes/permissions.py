from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import require_permissions
from backend.api.schemas.permissions import (
    RolePermissionMatrixItem,
    RolePermissionUpdateRequest,
)
from backend.application.services.permission_service import PermissionService
from backend.core.config import get_settings
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_permission_service() -> PermissionService:
    return PermissionService()


def _normalize_role_matrix_row(row: dict) -> dict:
    payload = dict(row or {})
    payload["discord_role_id"] = str(payload.get("discord_role_id") or "")
    payload["guild_id"] = str(payload.get("guild_id") or "")
    payload["assigned_permissions"] = [
        str(item).strip()
        for item in (payload.get("assigned_permissions") or [])
        if str(item).strip()
    ]
    return payload


@router.get("/catalog", response_model=list[str])
async def list_permission_catalog(
    _: object = Depends(require_permissions("discord_role_permissions.read")),
    service: PermissionService = Depends(get_permission_service),
):
    settings = get_settings()
    cache_key = cache.build_key("permissions_catalog")
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [str(item) for item in cached]

    rows = await service.list_permission_catalog()
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(rows),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"permissions_role_matrix"},
    )
    return [str(item) for item in rows]


@router.get("/role-matrix", response_model=list[RolePermissionMatrixItem])
async def list_role_matrix(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sync: bool = Query(default=False),
    _: object = Depends(require_permissions("discord_role_permissions.read")),
    service: PermissionService = Depends(get_permission_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "permissions_role_matrix",
        {"limit": limit, "offset": offset},
    )
    if not sync:
        cached = await cache.get_json(cache_key)
        if cached is not None:
            return [RolePermissionMatrixItem(**_normalize_role_matrix_row(row)) for row in cached]

    rows = await service.list_role_matrix(limit=limit, offset=offset, sync_roles=sync)
    payload = [
        RolePermissionMatrixItem(**_normalize_role_matrix_row(row)).model_dump(mode="json")
        for row in rows
    ]
    if sync:
        await cache.invalidate_tags("permissions_role_matrix")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"permissions_role_matrix"},
    )
    return [RolePermissionMatrixItem(**_normalize_role_matrix_row(row)) for row in payload]


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
    await cache.invalidate_tags("permissions_role_matrix")
    return RolePermissionMatrixItem(**_normalize_role_matrix_row(row))
