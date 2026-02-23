from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import (
    get_current_principal,
    require_any_permissions,
    require_permissions,
)
from backend.api.schemas.vacations import (
    VacationCreateRequest,
    VacationPoliciesResponse,
    VacationResponse,
    VacationReviewRequest,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.vacation_service import VacationService
from backend.core.config import get_settings
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_vacation_service() -> VacationService:
    return VacationService()


@router.post("", response_model=VacationResponse)
async def submit_vacation_request(
    payload: VacationCreateRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("vacations.submit")),
    service: VacationService = Depends(get_vacation_service),
):
    row = await service.submit_request(
        requester_user_id=principal.user_id,
        leave_date=payload.leave_date,
        expected_return_date=payload.expected_return_date,
        target_group=payload.target_group,
        reason=payload.reason,
    )
    await cache.invalidate_tags(
        "vacations",
        "review_queue",
        f"vacations_user:{principal.user_id}",
        "notifications",
    )
    return VacationResponse(**row)


@router.get("", response_model=list[VacationResponse])
async def list_vacation_requests(
    status: str | None = Query(default=None),
    player_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(require_permissions("vacations.read")),
    service: VacationService = Depends(get_vacation_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "vacations_list",
        {
            "status": status,
            "player_id": player_id,
            "limit": limit,
            "offset": offset,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [VacationResponse(**row) for row in cached]

    rows = await service.list_requests(
        status=status,
        player_id=player_id,
        requester_user_id=None,
        limit=limit,
        offset=offset,
    )
    payload = [VacationResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"vacations"},
    )
    return [VacationResponse(**row) for row in payload]


@router.get("/mine", response_model=list[VacationResponse])
async def list_my_vacation_requests(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: AuthenticatedPrincipal = Depends(
        require_any_permissions("vacations.submit", "vacations.read")
    ),
    service: VacationService = Depends(get_vacation_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "vacations_mine",
        {
            "user_id": principal.user_id,
            "status": status,
            "limit": limit,
            "offset": offset,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [VacationResponse(**row) for row in cached]

    rows = await service.list_requests(
        status=status,
        player_id=None,
        requester_user_id=principal.user_id,
        limit=limit,
        offset=offset,
    )
    payload = [VacationResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"vacations", f"vacations_user:{principal.user_id}"},
    )
    return [VacationResponse(**row) for row in payload]


@router.get("/policies", response_model=VacationPoliciesResponse)
async def get_vacation_policies(
    _: object = Depends(require_any_permissions("vacations.read", "vacations.submit")),
    service: VacationService = Depends(get_vacation_service),
):
    return VacationPoliciesResponse(**(await service.get_policies()))


@router.get("/{public_id}", response_model=VacationResponse)
async def get_vacation_request(
    public_id: str,
    _: object = Depends(require_permissions("vacations.read")),
    service: VacationService = Depends(get_vacation_service),
):
    row = await service.get_request(public_id=public_id)
    return VacationResponse(**row)


@router.post("/{public_id}/approve", response_model=VacationResponse)
async def approve_vacation_request(
    public_id: str,
    payload: VacationReviewRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("vacations.approve")),
    service: VacationService = Depends(get_vacation_service),
):
    row = await service.approve_request(
        public_id=public_id,
        reviewer_user_id=principal.user_id,
        review_comment=payload.review_comment,
    )
    await cache.invalidate_tags(
        "vacations",
        "review_queue",
        "public_roster",
        "public_metrics",
        f"vacations_user:{row['requester_user_id']}",
        "notifications",
    )
    return VacationResponse(**row)


@router.post("/{public_id}/deny", response_model=VacationResponse)
async def deny_vacation_request(
    public_id: str,
    payload: VacationReviewRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("vacations.deny")),
    service: VacationService = Depends(get_vacation_service),
):
    row = await service.deny_request(
        public_id=public_id,
        reviewer_user_id=principal.user_id,
        review_comment=payload.review_comment,
    )
    await cache.invalidate_tags(
        "vacations",
        "review_queue",
        f"vacations_user:{row['requester_user_id']}",
        "notifications",
    )
    return VacationResponse(**row)


@router.post("/{public_id}/cancel", response_model=VacationResponse)
async def cancel_vacation_request(
    public_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("vacations.cancel")),
    service: VacationService = Depends(get_vacation_service),
):
    row = await service.cancel_request(
        public_id=public_id,
        requester_user_id=principal.user_id,
    )
    await cache.invalidate_tags(
        "vacations",
        "review_queue",
        f"vacations_user:{principal.user_id}",
    )
    return VacationResponse(**row)


@router.post("/{public_id}/returned", response_model=VacationResponse)
async def mark_vacation_returned(
    public_id: str,
    payload: VacationReviewRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("vacations.approve")),
    service: VacationService = Depends(get_vacation_service),
):
    row = await service.mark_returned(
        public_id=public_id,
        reviewer_user_id=principal.user_id,
        review_comment=payload.review_comment,
    )
    await cache.invalidate_tags(
        "vacations",
        "review_queue",
        "public_roster",
        "public_metrics",
        f"vacations_user:{row['requester_user_id']}",
        "notifications",
    )
    return VacationResponse(**row)
