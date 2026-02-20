from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import get_current_principal, require_permissions
from backend.api.schemas.admin import (
    AuditTimelineResponse,
    DashboardSummaryResponse,
    ReviewQueueResponse,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.admin_service import AdminService
from backend.core.config import get_settings
from backend.core.errors import ApiException
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()

REVIEW_QUEUE_ACCESS_KEYS = {
    "applications.review",
    "applications.decision.accept",
    "applications.decision.decline",
    "orders.review",
    "orders.decision.accept",
    "orders.decision.deny",
    "activities.approve",
    "activities.reject",
    "vacations.approve",
    "vacations.deny",
    "blacklist_removal_requests.review",
    "verification_requests.review",
    "config_change.approve",
    "owner.override",
}


def get_admin_service() -> AdminService:
    return AdminService()


async def require_review_queue_access(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> AuthenticatedPrincipal:
    if principal.is_owner:
        return principal
    if REVIEW_QUEUE_ACCESS_KEYS.intersection(set(principal.permissions)):
        return principal
    raise ApiException(
        status_code=403,
        error_code="REVIEW_QUEUE_ACCESS_DENIED",
        message="Missing review permissions to access unified review queue",
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    _: object = Depends(require_permissions("audit.read")),
    service: AdminService = Depends(get_admin_service),
):
    settings = get_settings()
    cache_key = cache.build_key("admin_dashboard_summary")
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return DashboardSummaryResponse(**cached)

    result = await service.get_dashboard_summary()
    payload = DashboardSummaryResponse(**result).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"review_queue"},
    )
    return DashboardSummaryResponse(**payload)


@router.get("/review-queue", response_model=ReviewQueueResponse)
async def review_queue(
    item_types: list[str] | None = Query(default=None, alias="item_type"),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    pending_only: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: AuthenticatedPrincipal = Depends(require_review_queue_access),
    service: AdminService = Depends(get_admin_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "admin_review_queue",
        {
            "user_id": principal.user_id,
            "item_types": item_types or [],
            "status": status,
            "search": search,
            "pending_only": pending_only,
            "limit": limit,
            "offset": offset,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return ReviewQueueResponse(**cached)

    result = await service.list_review_queue(
        item_types=item_types,
        status=status,
        search=search,
        pending_only=pending_only,
        limit=limit,
        offset=offset,
    )
    payload = ReviewQueueResponse(**result).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"review_queue"},
    )
    return ReviewQueueResponse(**payload)


@router.get("/audit/timeline", response_model=AuditTimelineResponse)
async def audit_timeline(
    event_types: list[str] | None = Query(default=None, alias="event_type"),
    actor_user_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(require_permissions("audit.read")),
    service: AdminService = Depends(get_admin_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "admin_audit_timeline",
        {
            "event_types": event_types or [],
            "actor_user_id": actor_user_id,
            "search": search,
            "limit": limit,
            "offset": offset,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return AuditTimelineResponse(**cached)

    result = await service.list_audit_timeline(
        event_types=event_types,
        actor_user_id=actor_user_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    payload = AuditTimelineResponse(**result).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"audit"},
    )
    return AuditTimelineResponse(**payload)
