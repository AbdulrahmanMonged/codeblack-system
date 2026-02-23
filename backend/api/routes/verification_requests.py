from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import (
    get_current_principal,
    require_any_permissions,
    require_permissions,
)
from backend.api.schemas.verification_requests import (
    VerificationRequestCreate,
    VerificationRequestResponse,
    VerificationReviewRequest,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.verification_service import VerificationService
from backend.core.config import get_settings
from backend.core.errors import ApiException
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_verification_service() -> VerificationService:
    return VerificationService()


@router.post("", response_model=VerificationRequestResponse)
async def create_verification_request(
    payload: VerificationRequestCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("verification_requests.create")),
    service: VerificationService = Depends(get_verification_service),
):
    row = await service.create_request(
        principal=principal,
        account_name=payload.account_name,
        mta_serial=payload.mta_serial,
        forum_url=payload.forum_url,
    )
    await cache.invalidate_tags(
        "verification_requests",
        "review_queue",
        f"verification_requests:{principal.user_id}",
        "notifications",
    )
    return VerificationRequestResponse(**row)


@router.get("/me", response_model=VerificationRequestResponse | None)
async def get_my_verification_request(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("verification_requests.read_own")),
    service: VerificationService = Depends(get_verification_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "verification_request_me",
        {"user_id": principal.user_id},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return VerificationRequestResponse(**cached) if cached else None

    row = await service.get_latest_for_user(user_id=principal.user_id)
    if row is None:
        await cache.set_json(
            key=cache_key,
            value=None,
            ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
            tags={"verification_requests", f"verification_requests:{principal.user_id}"},
        )
        return None
    payload = VerificationRequestResponse(**row).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"verification_requests", f"verification_requests:{principal.user_id}"},
    )
    return VerificationRequestResponse(**payload)


@router.get("/{public_id}", response_model=VerificationRequestResponse)
async def get_verification_request(
    public_id: str,
    _: object = Depends(
        require_any_permissions("verification_requests.read", "verification_requests.review")
    ),
    service: VerificationService = Depends(get_verification_service),
):
    row = await service.get_by_public_id(public_id=public_id)
    return VerificationRequestResponse(**row)


@router.get("", response_model=list[VerificationRequestResponse])
async def list_verification_requests(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(
        require_any_permissions("verification_requests.read", "verification_requests.review")
    ),
    service: VerificationService = Depends(get_verification_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "verification_requests_list",
        {"status": status, "limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [VerificationRequestResponse(**row) for row in cached]

    rows = await service.list_requests(status=status, limit=limit, offset=offset)
    payload = [VerificationRequestResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"verification_requests", "review_queue"},
    )
    return [VerificationRequestResponse(**row) for row in payload]


@router.post("/{public_id}/approve", response_model=VerificationRequestResponse)
async def approve_verification_request(
    public_id: str,
    payload: VerificationReviewRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("verification_requests.review")),
    service: VerificationService = Depends(get_verification_service),
):
    row = await service.approve_request(
        public_id=public_id,
        reviewer_user_id=principal.user_id,
        review_comment=payload.review_comment,
    )
    await cache.invalidate_tags(
        "verification_requests",
        "review_queue",
        f"verification_requests:{row['user_id']}",
        f"user_session:{row['user_id']}",
        "notifications",
    )
    return VerificationRequestResponse(**row)


@router.post("/{public_id}/deny", response_model=VerificationRequestResponse)
async def deny_verification_request(
    public_id: str,
    payload: VerificationReviewRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("verification_requests.review")),
    service: VerificationService = Depends(get_verification_service),
):
    if not payload.review_comment or len(payload.review_comment.strip()) < 3:
        raise ApiException(
            status_code=422,
            error_code="VERIFICATION_REVIEW_COMMENT_REQUIRED",
            message="review_comment is required for denial",
        )
    row = await service.deny_request(
        public_id=public_id,
        reviewer_user_id=principal.user_id,
        review_comment=payload.review_comment,
    )
    await cache.invalidate_tags(
        "verification_requests",
        "review_queue",
        f"verification_requests:{row['user_id']}",
        "notifications",
    )
    return VerificationRequestResponse(**row)
