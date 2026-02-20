from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder

from backend.api.deps.precheck import (
    build_precheck_cache_key,
    normalize_account_name,
    resolve_precheck_actor_key,
)
from backend.api.deps.auth import (
    get_optional_principal,
    require_permissions,
)
from backend.api.schemas.applications import (
    ApplicationDecisionRequest,
    ApplicationEligibilityResponse,
    ApplicationPoliciesResponse,
    ApplicationPoliciesUpdateRequest,
    ApplicationResponse,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.application_service import ApplicationService
from backend.core.config import get_settings
from backend.core.errors import ApiException
from backend.infrastructure.cache.redis_cache import cache
from backend.infrastructure.storage.uploader import StorageUploader

router = APIRouter()
APPLICATION_ELIGIBILITY_PRECHECK_SCOPE = "applications_eligibility_precheck"


def get_application_service() -> ApplicationService:
    return ApplicationService()


def _eligibility_precheck_ttl_seconds() -> int:
    settings = get_settings()
    return max(1, int(settings.BACKEND_ELIGIBILITY_PRECHECK_TTL_SECONDS))


async def _cache_application_eligibility_result(
    *,
    request: Request,
    principal: AuthenticatedPrincipal | None,
    account_name: str,
    result: dict,
) -> None:
    settings = get_settings()
    if not settings.BACKEND_CACHE_ENABLED:
        return
    actor_key = resolve_precheck_actor_key(
        request,
        user_id=principal.user_id if principal else None,
    )
    cache_key = build_precheck_cache_key(
        scope=APPLICATION_ELIGIBILITY_PRECHECK_SCOPE,
        account_name=account_name,
        actor_key=actor_key,
    )
    await cache.set_json(
        key=cache_key,
        value={
            "allowed": bool(result.get("allowed")),
            "status": str(result.get("status") or ""),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
        ttl_seconds=_eligibility_precheck_ttl_seconds(),
        tags={"applications", "eligibility_precheck"},
    )


async def _require_application_eligibility_precheck(
    *,
    request: Request,
    principal: AuthenticatedPrincipal | None,
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
    actor_key = resolve_precheck_actor_key(
        request,
        user_id=principal.user_id if principal else None,
    )
    cache_key = build_precheck_cache_key(
        scope=APPLICATION_ELIGIBILITY_PRECHECK_SCOPE,
        account_name=normalized_account_name,
        actor_key=actor_key,
    )
    marker = await cache.get_json(cache_key)
    if marker is None:
        raise ApiException(
            status_code=403,
            error_code="ELIGIBILITY_CHECK_REQUIRED",
            message="Complete eligibility check before submitting an application",
        )
    if not bool(marker.get("allowed")):
        raise ApiException(
            status_code=403,
            error_code="ELIGIBILITY_CHECK_NOT_PASSED",
            message="Latest eligibility check did not pass",
            details={"status": marker.get("status")},
        )
    return cache_key


@router.post("", response_model=ApplicationResponse)
async def submit_application(
    request: Request,
    in_game_nickname: str = Form(min_length=2, max_length=255),
    account_name: str = Form(min_length=2, max_length=255),
    mta_serial: str = Form(min_length=10, max_length=64),
    english_skill: int = Form(ge=0, le=10),
    has_second_account: bool = Form(default=False),
    second_account_name: str | None = Form(default=None, max_length=255),
    cit_journey: str = Form(min_length=10),
    former_groups_reason: str = Form(min_length=5),
    why_join: str = Form(min_length=5),
    captcha_token: str | None = Form(default=None),
    punishlog_image: UploadFile = File(...),
    stats_image: UploadFile = File(...),
    history_image: UploadFile = File(...),
    principal: AuthenticatedPrincipal | None = Depends(get_optional_principal),
    service: ApplicationService = Depends(get_application_service),
):
    if principal is not None and not principal.is_owner:
        if "applications.create_member" not in principal.permissions:
            raise ApiException(
                status_code=403,
                error_code="PERMISSION_DENIED",
                message="Authenticated user lacks applications.create_member",
            )

    if has_second_account and not second_account_name:
        raise ApiException(
            status_code=422,
            error_code="SECOND_ACCOUNT_REQUIRED",
            message="second_account_name is required when has_second_account is true",
        )
    if not has_second_account:
        second_account_name = None

    eligibility_precheck_key = await _require_application_eligibility_precheck(
        request=request,
        principal=principal,
        account_name=account_name,
    )

    punishlog_bytes, punishlog_content_type, punishlog_ext = await _validate_image_upload(
        upload=punishlog_image,
        field_name="punishlog_image",
    )
    stats_bytes, stats_content_type, stats_ext = await _validate_image_upload(
        upload=stats_image,
        field_name="stats_image",
    )
    history_bytes, history_content_type, history_ext = await _validate_image_upload(
        upload=history_image,
        field_name="history_image",
    )

    upload_prefix = uuid4().hex
    account_segment = account_name.strip().lower()
    uploader = StorageUploader()
    punishlog_uploaded = await uploader.upload_bytes(
        key=f"applications/{account_segment}/{upload_prefix}_punishlog.{punishlog_ext}",
        data=punishlog_bytes,
        content_type=punishlog_content_type,
    )
    stats_uploaded = await uploader.upload_bytes(
        key=f"applications/{account_segment}/{upload_prefix}_stats.{stats_ext}",
        data=stats_bytes,
        content_type=stats_content_type,
    )
    history_uploaded = await uploader.upload_bytes(
        key=f"applications/{account_segment}/{upload_prefix}_history.{history_ext}",
        data=history_bytes,
        content_type=history_content_type,
    )

    ip_address = request.client.host if request.client else None
    row = await service.submit_application(
        payload={
            "in_game_nickname": in_game_nickname,
            "account_name": account_name,
            "mta_serial": mta_serial,
            "english_skill": english_skill,
            "has_second_account": has_second_account,
            "second_account_name": second_account_name,
            "cit_journey": cit_journey,
            "former_groups_reason": former_groups_reason,
            "why_join": why_join,
            "punishlog_url": punishlog_uploaded.url,
            "stats_url": stats_uploaded.url,
            "history_url": history_uploaded.url,
        },
        principal=principal,
        ip_address=ip_address,
        captcha_token=captcha_token,
    )
    await cache.invalidate_tags("applications", "review_queue")
    if eligibility_precheck_key:
        await cache.invalidate_key(eligibility_precheck_key)
    return ApplicationResponse(**row)


@router.get("/eligibility", response_model=ApplicationEligibilityResponse)
async def check_eligibility(
    request: Request,
    account_name: str = Query(min_length=2, max_length=255),
    principal: AuthenticatedPrincipal | None = Depends(get_optional_principal),
    service: ApplicationService = Depends(get_application_service),
):
    result = await service.check_eligibility(account_name=account_name)
    await _cache_application_eligibility_result(
        request=request,
        principal=principal,
        account_name=account_name,
        result=result,
    )
    return ApplicationEligibilityResponse(**result)


@router.get("/eligibility/me", response_model=ApplicationEligibilityResponse)
async def check_my_eligibility(
    request: Request,
    account_name: str = Query(min_length=2, max_length=255),
    principal: AuthenticatedPrincipal = Depends(require_permissions("applications.eligibility.read")),
    service: ApplicationService = Depends(get_application_service),
):
    result = await service.check_eligibility(account_name=account_name)
    await _cache_application_eligibility_result(
        request=request,
        principal=principal,
        account_name=account_name,
        result=result,
    )
    return ApplicationEligibilityResponse(**result)


@router.get("", response_model=list[ApplicationResponse])
async def list_applications(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: AuthenticatedPrincipal = Depends(require_permissions("applications.read_private")),
    service: ApplicationService = Depends(get_application_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "applications_list",
        {"status": status, "limit": limit, "offset": offset},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [ApplicationResponse(**row) for row in cached]

    rows = await service.list_applications(status=status, limit=limit, offset=offset)
    payload = [ApplicationResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"applications"},
    )
    return [ApplicationResponse(**row) for row in payload]


@router.get("/policies", response_model=ApplicationPoliciesResponse)
async def get_application_policies(
    _: AuthenticatedPrincipal = Depends(require_permissions("applications.policies.read")),
    service: ApplicationService = Depends(get_application_service),
):
    policies = await service.get_policies()
    return ApplicationPoliciesResponse(**policies)


@router.put("/policies", response_model=ApplicationPoliciesResponse)
async def update_application_policies(
    payload: ApplicationPoliciesUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("applications.policies.write")),
    service: ApplicationService = Depends(get_application_service),
):
    policies = await service.update_policies(
        actor_user_id=principal.user_id,
        default_cooldown_days=payload.default_cooldown_days,
        guest_max_submissions_per_24h=payload.guest_max_submissions_per_24h,
        captcha_enabled=payload.captcha_enabled,
        captcha_site_key=payload.captcha_site_key,
    )
    return ApplicationPoliciesResponse(**policies)


async def _validate_image_upload(
    *,
    upload: UploadFile,
    field_name: str,
) -> tuple[bytes, str, str]:
    allowed_types = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }
    content_type = upload.content_type or ""
    if content_type not in allowed_types:
        raise ApiException(
            status_code=422,
            error_code="INVALID_IMAGE_TYPE",
            message=f"{field_name} must be png, jpeg, or webp",
        )

    data = await upload.read()
    if not data:
        raise ApiException(
            status_code=422,
            error_code="EMPTY_IMAGE_FILE",
            message=f"{field_name} cannot be empty",
        )
    if len(data) > 10 * 1024 * 1024:
        raise ApiException(
            status_code=422,
            error_code="IMAGE_TOO_LARGE",
            message=f"{field_name} must be <= 10MB",
        )
    return data, content_type, allowed_types[content_type]


@router.get("/{public_id}", response_model=ApplicationResponse)
async def get_application(
    public_id: str,
    _: AuthenticatedPrincipal = Depends(require_permissions("applications.read_private")),
    service: ApplicationService = Depends(get_application_service),
):
    row = await service.get_application(public_id=public_id)
    return ApplicationResponse(**row)


@router.post("/{public_id}/decision", response_model=ApplicationResponse)
async def decide_application(
    public_id: str,
    payload: ApplicationDecisionRequest,
    principal: AuthenticatedPrincipal = Depends(require_permissions("applications.review")),
    service: ApplicationService = Depends(get_application_service),
):
    decision = payload.decision
    if decision == "accepted" and not principal.is_owner:
        if "applications.decision.accept" not in principal.permissions:
            raise ApiException(
                status_code=403,
                error_code="PERMISSION_DENIED",
                message="Missing applications.decision.accept permission",
            )
    if decision == "declined" and not principal.is_owner:
        if "applications.decision.decline" not in principal.permissions:
            raise ApiException(
                status_code=403,
                error_code="PERMISSION_DENIED",
                message="Missing applications.decision.decline permission",
            )

    row = await service.decide_application(
        public_id=public_id,
        reviewer_user_id=principal.user_id,
        decision=payload.decision,
        decision_reason=payload.decision_reason,
        reapply_policy=payload.reapply_policy,
        cooldown_days=payload.cooldown_days,
    )
    await cache.invalidate_tags(
        "applications",
        "review_queue",
        f"voting_context:application:{public_id}",
        f"voting_voters:application:{public_id}",
    )
    return ApplicationResponse(**row)
