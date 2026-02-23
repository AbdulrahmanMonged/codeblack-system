from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import require_permissions
from backend.api.schemas.common import OperationResponse
from backend.api.schemas.config_registry import (
    ConfigApproveRequest,
    ConfigChangeResponse,
    ConfigEntryResponse,
    ConfigMutationResponse,
    ConfigPreviewRequest,
    ConfigPreviewResponse,
    ConfigRollbackRequest,
    ConfigUpsertRequest,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.config_registry_service import ConfigRegistryService
from backend.core.config import get_settings
from backend.core.errors import ApiException
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_service() -> ConfigRegistryService:
    return ConfigRegistryService()


@router.get("/registry", response_model=list[ConfigEntryResponse])
async def list_registry(
    include_sensitive: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: AuthenticatedPrincipal = Depends(require_permissions("config_registry.read")),
    service: ConfigRegistryService = Depends(get_service),
):
    if include_sensitive and not principal.is_owner:
        raise ApiException(
            status_code=403,
            error_code="SENSITIVE_CONFIG_ACCESS_DENIED",
            message="Only owners can view sensitive config values",
        )

    settings = get_settings()
    cache_key = cache.build_key(
        "config_registry_entries",
        {
            "include_sensitive": include_sensitive,
            "limit": limit,
            "offset": offset,
            "user_id": principal.user_id,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [ConfigEntryResponse(**entry) for entry in cached]

    rows = await service.list_entries(
        include_sensitive=include_sensitive,
        limit=limit,
        offset=offset,
    )
    payload = [entry.model_dump(mode="json") for entry in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"config_registry", "config_changes"},
    )
    return [ConfigEntryResponse(**entry) for entry in payload]


@router.put("/registry/{key}", response_model=ConfigMutationResponse)
async def upsert_registry_key(
    key: str,
    payload: ConfigUpsertRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("config_registry.write")),
    service: ConfigRegistryService = Depends(get_service),
):
    result = await service.upsert_entry(
        key=key,
        value_json=payload.value_json,
        schema_version=payload.schema_version,
        is_sensitive=payload.is_sensitive,
        actor_user_id=principal.user_id,
        change_reason=payload.change_reason,
    )
    await cache.invalidate_tags("config_registry", "config_changes")
    return result


@router.post("/registry/{key}/preview", response_model=ConfigPreviewResponse)
async def preview_registry_key(
    key: str,
    payload: ConfigPreviewRequest,
    _: AuthenticatedPrincipal = Depends(require_permissions("config_registry.preview")),
    service: ConfigRegistryService = Depends(get_service),
):
    return await service.preview_entry(
        key=key,
        value_json=payload.value_json,
        schema_version=payload.schema_version,
        is_sensitive=payload.is_sensitive,
    )


@router.get("/changes", response_model=list[ConfigChangeResponse])
async def list_registry_changes(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    include_sensitive_values: bool = Query(default=False),
    principal: AuthenticatedPrincipal = Depends(require_permissions("config_registry.read")),
    service: ConfigRegistryService = Depends(get_service),
):
    if include_sensitive_values and not principal.is_owner:
        raise ApiException(
            status_code=403,
            error_code="SENSITIVE_CONFIG_ACCESS_DENIED",
            message="Only owners can view sensitive config change values",
        )

    settings = get_settings()
    cache_key = cache.build_key(
        "config_registry_changes",
        {
            "include_sensitive_values": include_sensitive_values,
            "limit": limit,
            "offset": offset,
            "user_id": principal.user_id,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [ConfigChangeResponse(**change) for change in cached]

    rows = await service.list_changes(
        limit=limit,
        offset=offset,
        include_sensitive_values=include_sensitive_values,
    )
    payload = [change.model_dump(mode="json") for change in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"config_registry", "config_changes"},
    )
    return [ConfigChangeResponse(**change) for change in payload]


@router.post("/registry/{key}/rollback", response_model=OperationResponse)
async def rollback_registry_key(
    key: str,
    payload: ConfigRollbackRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("config_registry.rollback")),
    service: ConfigRegistryService = Depends(get_service),
):
    await service.rollback_to_change(
        key=key,
        change_id=payload.change_id,
        actor_user_id=principal.user_id,
        change_reason=payload.change_reason,
    )
    await cache.invalidate_tags("config_registry", "config_changes")
    return OperationResponse(ok=True, message="Rollback completed")


@router.post("/changes/{change_id}/approve", response_model=ConfigMutationResponse)
async def approve_registry_change(
    change_id: int,
    payload: ConfigApproveRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("config_change.approve")),
    service: ConfigRegistryService = Depends(get_service),
):
    result = await service.approve_change(
        change_id=change_id,
        approver_user_id=principal.user_id,
        change_reason=payload.change_reason,
    )
    await cache.invalidate_tags("config_registry", "config_changes")
    return result
