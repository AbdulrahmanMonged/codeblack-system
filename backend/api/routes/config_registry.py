from fastapi import APIRouter, Depends, Query

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
from backend.core.errors import ApiException

router = APIRouter()


def get_service() -> ConfigRegistryService:
    return ConfigRegistryService()


@router.get("/registry", response_model=list[ConfigEntryResponse])
async def list_registry(
    include_sensitive: bool = Query(default=False),
    principal: AuthenticatedPrincipal = Depends(require_permissions("config_registry.read")),
    service: ConfigRegistryService = Depends(get_service),
):
    if include_sensitive and not principal.is_owner:
        raise ApiException(
            status_code=403,
            error_code="SENSITIVE_CONFIG_ACCESS_DENIED",
            message="Only owners can view sensitive config values",
        )
    return await service.list_entries(include_sensitive=include_sensitive)


@router.put("/registry/{key}", response_model=ConfigMutationResponse)
async def upsert_registry_key(
    key: str,
    payload: ConfigUpsertRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("config_registry.write")),
    service: ConfigRegistryService = Depends(get_service),
):
    return await service.upsert_entry(
        key=key,
        value_json=payload.value_json,
        schema_version=payload.schema_version,
        is_sensitive=payload.is_sensitive,
        actor_user_id=principal.user_id,
        change_reason=payload.change_reason,
    )


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
    return await service.list_changes(
        limit=limit,
        include_sensitive_values=include_sensitive_values,
    )


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
    return OperationResponse(ok=True, message="Rollback completed")


@router.post("/changes/{change_id}/approve", response_model=ConfigMutationResponse)
async def approve_registry_change(
    change_id: int,
    payload: ConfigApproveRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("config_change.approve")),
    service: ConfigRegistryService = Depends(get_service),
):
    return await service.approve_change(
        change_id=change_id,
        approver_user_id=principal.user_id,
        change_reason=payload.change_reason,
    )

