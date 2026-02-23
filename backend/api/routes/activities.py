from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import get_current_principal, require_permissions
from backend.api.schemas.activities import (
    ActivityCreateRequest,
    ActivityPublishRequest,
    ActivityPublishResponse,
    ActivityParticipantCreateRequest,
    ActivityParticipantResponse,
    ActivityResponse,
    ActivityReviewRequest,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.activity_service import ActivityService
from backend.core.config import get_settings
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_activity_service() -> ActivityService:
    return ActivityService()


@router.post("", response_model=ActivityResponse)
async def create_activity(
    payload: ActivityCreateRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("activities.create")),
    service: ActivityService = Depends(get_activity_service),
):
    row = await service.create_activity(
        activity_type=payload.activity_type,
        title=payload.title,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
        created_by_user_id=principal.user_id,
        scheduled_for=payload.scheduled_for,
    )
    await cache.invalidate_tags("activities", "review_queue")
    return ActivityResponse(**row)


@router.post("/{public_id}/publish", response_model=ActivityPublishResponse)
async def publish_activity(
    public_id: str,
    payload: ActivityPublishRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("activities.publish_forum")),
    service: ActivityService = Depends(get_activity_service),
):
    row = await service.publish_to_forum(
        public_id=public_id,
        actor_user_id=principal.user_id,
        forum_topic_id=payload.forum_topic_id,
        force_retry=payload.force_retry,
    )
    await cache.invalidate_tags("activities", "review_queue")
    return ActivityPublishResponse(
        activity=ActivityResponse(**row["activity"]),
        dispatch=row["dispatch"],
    )


@router.get("", response_model=list[ActivityResponse])
async def list_activities(
    status: str | None = Query(default=None),
    activity_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(require_permissions("activities.read")),
    service: ActivityService = Depends(get_activity_service),
):
    settings = get_settings()
    cache_key = cache.build_key(
        "activities_list",
        {
            "status": status,
            "activity_type": activity_type,
            "limit": limit,
            "offset": offset,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [ActivityResponse(**row) for row in cached]

    rows = await service.list_activities(
        status=status,
        activity_type=activity_type,
        limit=limit,
        offset=offset,
    )
    payload = [ActivityResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_AUTH_LIST_TTL_SECONDS,
        tags={"activities"},
    )
    return [ActivityResponse(**row) for row in payload]


@router.get("/{public_id}", response_model=ActivityResponse)
async def get_activity(
    public_id: str,
    _: object = Depends(require_permissions("activities.read")),
    service: ActivityService = Depends(get_activity_service),
):
    row = await service.get_activity(public_id=public_id)
    return ActivityResponse(**row)


@router.post("/{public_id}/approve", response_model=ActivityResponse)
async def approve_activity(
    public_id: str,
    payload: ActivityReviewRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("activities.approve")),
    service: ActivityService = Depends(get_activity_service),
):
    row = await service.approve_activity(
        public_id=public_id,
        approver_user_id=principal.user_id,
        approval_comment=payload.approval_comment,
        scheduled_for=payload.scheduled_for,
    )
    await cache.invalidate_tags("activities", "review_queue")
    return ActivityResponse(**row)


@router.post("/{public_id}/reject", response_model=ActivityResponse)
async def reject_activity(
    public_id: str,
    payload: ActivityReviewRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("activities.reject")),
    service: ActivityService = Depends(get_activity_service),
):
    row = await service.reject_activity(
        public_id=public_id,
        approver_user_id=principal.user_id,
        approval_comment=payload.approval_comment,
    )
    await cache.invalidate_tags("activities", "review_queue")
    return ActivityResponse(**row)


@router.post("/{public_id}/participants", response_model=ActivityParticipantResponse)
async def add_activity_participant(
    public_id: str,
    payload: ActivityParticipantCreateRequest,
    _: object = Depends(require_permissions("activities.manage_participants")),
    service: ActivityService = Depends(get_activity_service),
):
    row = await service.add_participant(
        public_id=public_id,
        player_id=payload.player_id,
        participant_role=payload.participant_role,
        attendance_status=payload.attendance_status,
        notes=payload.notes,
    )
    await cache.invalidate_tags("activities")
    return ActivityParticipantResponse(**row)
