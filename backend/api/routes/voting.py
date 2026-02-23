from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import get_current_principal, require_permissions
from backend.api.schemas.applications import (
    ApplicationDecisionRequest,
    ApplicationResponse,
)
from backend.api.schemas.voting import (
    VotingContextResponse,
    VotingModerationRequest,
    VotingResetRequest,
    VotingResetResponse,
    VotingStateTransitionResponse,
    VotingVotersResponse,
    VotingVoteRequest,
    VotingVoteResponse,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.application_service import ApplicationService
from backend.core.errors import ApiException
from backend.core.config import get_settings
from backend.application.services.voting_service import VotingService
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_voting_service() -> VotingService:
    return VotingService()


def get_application_service() -> ApplicationService:
    return ApplicationService()


@router.post("/application/{application_id}/vote", response_model=VotingVoteResponse)
async def cast_application_vote(
    application_id: str,
    payload: VotingVoteRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("voting.cast")),
    service: VotingService = Depends(get_voting_service),
):
    row = await service.cast_vote(
        context_type="application",
        context_id=application_id,
        voter_user_id=principal.user_id,
        choice=payload.choice,
        comment_text=payload.comment_text,
    )
    await cache.invalidate_tags(
        f"voting_context:application:{application_id}",
        f"voting_voters:application:{application_id}",
        "applications",
        "review_queue",
    )
    return VotingVoteResponse(**row)


@router.get("/application/{application_id}/voters", response_model=VotingVotersResponse)
async def list_application_voters(
    application_id: str,
    _: object = Depends(require_permissions("voting.list_voters")),
    service: VotingService = Depends(get_voting_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "voting_voters",
        {"context_type": "application", "context_id": application_id},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return VotingVotersResponse(**cached)

    row = await service.list_voters(
        context_type="application",
        context_id=application_id,
    )
    payload = VotingVotersResponse(**row).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_VOTING_TTL_SECONDS,
        tags={f"voting_voters:application:{application_id}"},
    )
    return VotingVotersResponse(**payload)


@router.post("/application/{application_id}/decision", response_model=ApplicationResponse)
async def decide_application_from_voting_context(
    application_id: str,
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
        public_id=application_id,
        reviewer_user_id=principal.user_id,
        decision=payload.decision,
        decision_reason=payload.decision_reason,
        reapply_policy=payload.reapply_policy,
        cooldown_days=payload.cooldown_days,
    )
    await cache.invalidate_tags(
        f"voting_context:application:{application_id}",
        f"voting_voters:application:{application_id}",
        "applications",
        "review_queue",
    )
    return ApplicationResponse(**row)


@router.get("/{context_type}/{context_id}", response_model=VotingContextResponse)
async def get_voting_context(
    context_type: str,
    context_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("voting.read")),
    service: VotingService = Depends(get_voting_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "voting_context",
        {
            "context_type": context_type,
            "context_id": context_id,
            "user_id": principal.user_id,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return VotingContextResponse(**cached)

    row = await service.get_context(
        context_type=context_type,
        context_id=context_id,
        principal_user_id=principal.user_id,
    )
    payload = VotingContextResponse(**row).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_VOTING_TTL_SECONDS,
        tags={f"voting_context:{context_type}:{context_id}"},
    )
    return VotingContextResponse(**payload)


@router.post("/{context_type}/{context_id}/vote", response_model=VotingVoteResponse)
async def cast_vote(
    context_type: str,
    context_id: str,
    payload: VotingVoteRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("voting.cast")),
    service: VotingService = Depends(get_voting_service),
):
    row = await service.cast_vote(
        context_type=context_type,
        context_id=context_id,
        voter_user_id=principal.user_id,
        choice=payload.choice,
        comment_text=payload.comment_text,
    )
    await cache.invalidate_tags(
        f"voting_context:{context_type}:{context_id}",
        f"voting_voters:{context_type}:{context_id}",
        "applications",
        "review_queue",
    )
    return VotingVoteResponse(**row)


@router.get("/{context_type}/{context_id}/voters", response_model=VotingVotersResponse)
async def list_voters(
    context_type: str,
    context_id: str,
    _: object = Depends(require_permissions("voting.list_voters")),
    service: VotingService = Depends(get_voting_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "voting_voters",
        {"context_type": context_type, "context_id": context_id},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return VotingVotersResponse(**cached)

    row = await service.list_voters(
        context_type=context_type,
        context_id=context_id,
    )
    payload = VotingVotersResponse(**row).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_VOTING_TTL_SECONDS,
        tags={f"voting_voters:{context_type}:{context_id}"},
    )
    return VotingVotersResponse(**payload)


@router.post("/{context_type}/{context_id}/close", response_model=VotingStateTransitionResponse)
async def close_voting(
    context_type: str,
    context_id: str,
    payload: VotingModerationRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("voting.close")),
    service: VotingService = Depends(get_voting_service),
):
    row = await service.close_context(
        context_type=context_type,
        context_id=context_id,
        actor_user_id=principal.user_id,
        reason=payload.reason,
    )
    await cache.invalidate_tags(
        f"voting_context:{context_type}:{context_id}",
        f"voting_voters:{context_type}:{context_id}",
        "applications",
        "review_queue",
    )
    return VotingStateTransitionResponse(**row)


@router.post("/{context_type}/{context_id}/reopen", response_model=VotingStateTransitionResponse)
async def reopen_voting(
    context_type: str,
    context_id: str,
    payload: VotingModerationRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("voting.reopen")),
    service: VotingService = Depends(get_voting_service),
):
    row = await service.reopen_context(
        context_type=context_type,
        context_id=context_id,
        actor_user_id=principal.user_id,
        reason=payload.reason,
    )
    await cache.invalidate_tags(
        f"voting_context:{context_type}:{context_id}",
        f"voting_voters:{context_type}:{context_id}",
        "applications",
        "review_queue",
    )
    return VotingStateTransitionResponse(**row)


@router.post("/{context_type}/{context_id}/reset", response_model=VotingResetResponse)
async def reset_voting(
    context_type: str,
    context_id: str,
    payload: VotingResetRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("voting.reset")),
    service: VotingService = Depends(get_voting_service),
):
    row = await service.reset_context(
        context_type=context_type,
        context_id=context_id,
        actor_user_id=principal.user_id,
        reason=payload.reason,
        reopen=payload.reopen,
    )
    await cache.invalidate_tags(
        f"voting_context:{context_type}:{context_id}",
        f"voting_voters:{context_type}:{context_id}",
        "applications",
        "review_queue",
    )
    return VotingResetResponse(**row)
