from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder

from backend.api.deps.precheck import (
    build_precheck_cache_key,
    normalize_account_name,
    resolve_precheck_actor_key,
)
from backend.api.deps.auth import get_current_principal, require_permissions
from backend.api.schemas.blacklist import (
    BlacklistRemovalCheckResponse,
    BlacklistCreateRequest,
    BlacklistEntryResponse,
    BlacklistRemovalRequestCreate,
    BlacklistRemovalRequestResponse,
    BlacklistRemovalReviewRequest,
    BlacklistRemoveRequest,
    BlacklistUpdateRequest,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.blacklist_service import BlacklistService
from backend.core.config import get_settings
from backend.core.errors import ApiException
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()
BLACKLIST_REMOVAL_PRECHECK_SCOPE = "blacklist_removal_precheck"


def get_blacklist_service() -> BlacklistService:
    return BlacklistService()


def _eligibility_precheck_ttl_seconds() -> int:
    settings = get_settings()
    return max(1, int(settings.BACKEND_ELIGIBILITY_PRECHECK_TTL_SECONDS))


async def _cache_blacklist_removal_check_result(
    *,
    request: Request,
    account_name: str,
    result: dict,
) -> None:
    settings = get_settings()
    if not settings.BACKEND_CACHE_ENABLED:
        return
    actor_key = resolve_precheck_actor_key(request)
    cache_key = build_precheck_cache_key(
        scope=BLACKLIST_REMOVAL_PRECHECK_SCOPE,
        account_name=account_name,
        actor_key=actor_key,
    )
    await cache.set_json(
        key=cache_key,
        value={
            "is_blacklisted": bool(result.get("is_blacklisted")),
            "can_submit": bool(result.get("can_submit")),
            "status_message": str(result.get("status_message") or ""),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
        ttl_seconds=_eligibility_precheck_ttl_seconds(),
        tags={"blacklist", "eligibility_precheck"},
    )


async def _require_blacklist_removal_precheck(
    *,
    request: Request,
    account_name: str,
) -> str | None:
    settings = get_settings()
    if not settings.BACKEND_CACHE_ENABLED:
        raise ApiException(
            status_code=500,
            error_code="ELIGIBILITY_PRECHECK_CACHE_DISABLED",
            message="Eligibility precheck enforcement requires BACKEND_CACHE_ENABLED=true",
        )

    normalized_account_name = normalize_account_name(account_name)
    actor_key = resolve_precheck_actor_key(request)
    cache_key = build_precheck_cache_key(
        scope=BLACKLIST_REMOVAL_PRECHECK_SCOPE,
        account_name=normalized_account_name,
        actor_key=actor_key,
    )
    marker = await cache.get_json(cache_key)
    if marker is None:
        raise ApiException(
            status_code=403,
            error_code="BLACKLIST_REMOVAL_CHECK_REQUIRED",
            message="Complete blacklist removal eligibility check before submitting",
        )
    if not bool(marker.get("is_blacklisted")) or not bool(marker.get("can_submit")):
        raise ApiException(
            status_code=403,
            error_code="BLACKLIST_REMOVAL_CHECK_NOT_PASSED",
            message="Latest blacklist removal eligibility check did not pass",
            details={"status_message": marker.get("status_message")},
        )
    return cache_key


@router.post("", response_model=BlacklistEntryResponse)
async def create_blacklist_entry(
    payload: BlacklistCreateRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("blacklist.add")),
    service: BlacklistService = Depends(get_blacklist_service),
):
    row = await service.create_entry(
        player_id=payload.player_id,
        blacklist_level=payload.blacklist_level,
        alias=payload.alias,
        identity=payload.identity,
        serial=payload.serial,
        roots=payload.roots,
        remarks=payload.remarks,
        actor_user_id=principal.user_id,
    )
    await cache.invalidate_tags("blacklist", "review_queue")
    return BlacklistEntryResponse(**row)


@router.get("", response_model=list[BlacklistEntryResponse])
async def list_blacklist_entries(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(require_permissions("blacklist.read")),
    service: BlacklistService = Depends(get_blacklist_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "blacklist_entries",
        {"status": status, "limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [BlacklistEntryResponse(**row) for row in cached]

    rows = await service.list_entries(status=status, limit=limit, offset=offset)
    payload = [BlacklistEntryResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"blacklist"},
    )
    return [BlacklistEntryResponse(**row) for row in payload]


@router.get("/removal-requests/check", response_model=BlacklistRemovalCheckResponse)
async def check_blacklist_removal_eligibility(
    request: Request,
    account_name: str = Query(min_length=2, max_length=255),
    service: BlacklistService = Depends(get_blacklist_service),
):
    row = await service.check_removal_eligibility(account_name=account_name)
    await _cache_blacklist_removal_check_result(
        request=request,
        account_name=account_name,
        result=row,
    )
    return BlacklistRemovalCheckResponse(**row)


@router.post("/removal-requests", response_model=BlacklistRemovalRequestResponse)
async def create_blacklist_removal_request(
    request: Request,
    payload: BlacklistRemovalRequestCreate,
    service: BlacklistService = Depends(get_blacklist_service),
):
    precheck_key = await _require_blacklist_removal_precheck(
        request=request,
        account_name=payload.account_name,
    )
    row = await service.create_removal_request(
        account_name=payload.account_name,
        request_text=payload.request_text,
    )
    await cache.invalidate_tags("blacklist", "review_queue")
    if precheck_key:
        await cache.invalidate_key(precheck_key)
    return BlacklistRemovalRequestResponse(**row)


@router.get("/removal-requests", response_model=list[BlacklistRemovalRequestResponse])
async def list_blacklist_removal_requests(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(require_permissions("blacklist_removal_requests.read")),
    service: BlacklistService = Depends(get_blacklist_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "blacklist_removal_requests",
        {"status": status, "limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [BlacklistRemovalRequestResponse(**row) for row in cached]

    rows = await service.list_removal_requests(status=status, limit=limit, offset=offset)
    payload = [BlacklistRemovalRequestResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"blacklist", "review_queue"},
    )
    return [BlacklistRemovalRequestResponse(**row) for row in payload]


@router.get("/removal-requests/{request_id}", response_model=BlacklistRemovalRequestResponse)
async def get_blacklist_removal_request(
    request_id: int,
    _: object = Depends(require_permissions("blacklist_removal_requests.read")),
    service: BlacklistService = Depends(get_blacklist_service),
):
    row = await service.get_removal_request(request_id=request_id)
    return BlacklistRemovalRequestResponse(**row)


@router.post("/removal-requests/{request_id}/approve", response_model=BlacklistRemovalRequestResponse)
async def approve_blacklist_removal_request(
    request_id: int,
    payload: BlacklistRemovalReviewRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("blacklist_removal_requests.review")),
    service: BlacklistService = Depends(get_blacklist_service),
):
    row = await service.review_removal_request(
        request_id=request_id,
        approve=True,
        review_comment=payload.review_comment,
        reviewer_user_id=principal.user_id,
    )
    await cache.invalidate_tags("blacklist", "review_queue")
    return BlacklistRemovalRequestResponse(**row)


@router.post("/removal-requests/{request_id}/deny", response_model=BlacklistRemovalRequestResponse)
async def deny_blacklist_removal_request(
    request_id: int,
    payload: BlacklistRemovalReviewRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("blacklist_removal_requests.review")),
    service: BlacklistService = Depends(get_blacklist_service),
):
    row = await service.review_removal_request(
        request_id=request_id,
        approve=False,
        review_comment=payload.review_comment,
        reviewer_user_id=principal.user_id,
    )
    await cache.invalidate_tags("blacklist", "review_queue")
    return BlacklistRemovalRequestResponse(**row)


@router.patch("/{entry_id}", response_model=BlacklistEntryResponse)
async def update_blacklist_entry(
    entry_id: int,
    payload: BlacklistUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("blacklist.update")),
    service: BlacklistService = Depends(get_blacklist_service),
):
    row = await service.update_entry(
        entry_id=entry_id,
        blacklist_level=payload.blacklist_level,
        alias=payload.alias,
        serial=payload.serial,
        roots=payload.roots,
        remarks=payload.remarks,
        actor_user_id=principal.user_id,
    )
    await cache.invalidate_tags("blacklist", "review_queue")
    return BlacklistEntryResponse(**row)


@router.post("/{entry_id}/remove", response_model=BlacklistEntryResponse)
async def remove_blacklist_entry(
    entry_id: int,
    payload: BlacklistRemoveRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("blacklist.remove")),
    service: BlacklistService = Depends(get_blacklist_service),
):
    row = await service.remove_entry(
        entry_id=entry_id,
        actor_user_id=principal.user_id,
        reason=payload.reason,
    )
    await cache.invalidate_tags("blacklist", "review_queue")
    return BlacklistEntryResponse(**row)
