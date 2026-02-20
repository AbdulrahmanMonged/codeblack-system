from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from backend.api.deps.auth import get_current_principal, require_permissions
from backend.api.schemas.notifications import (
    NotificationBroadcastRequest,
    NotificationBroadcastResponse,
    NotificationDeleteResponse,
    NotificationMarkAllReadResponse,
    NotificationResponse,
    NotificationTargetedSendRequest,
    NotificationTargetedSendResponse,
    NotificationUnreadCountResponse,
)
from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.notification_service import NotificationService
from backend.core.config import get_settings
from backend.infrastructure.cache.redis_cache import cache

router = APIRouter()


def get_notification_service() -> NotificationService:
    return NotificationService()


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("notifications.read")),
    service: NotificationService = Depends(get_notification_service),
):
    settings = get_settings()
    user_tag = f"notifications:{principal.user_id}"
    cache_key = cache.build_key(
        "notifications_list",
        {
            "user_id": principal.user_id,
            "unread_only": unread_only,
            "limit": limit,
            "offset": offset,
        },
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return [NotificationResponse(**row) for row in cached]

    rows = await service.list_notifications(
        user_id=principal.user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    payload = [NotificationResponse(**row).model_dump(mode="json") for row in rows]
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_NOTIFICATIONS_TTL_SECONDS,
        tags={"notifications", user_tag},
    )
    return [NotificationResponse(**row) for row in payload]


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def notifications_unread_count(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("notifications.read")),
    service: NotificationService = Depends(get_notification_service),
):
    settings = get_settings()
    user_tag = f"notifications:{principal.user_id}"
    cache_key = cache.build_key(
        "notifications_unread_count",
        {"user_id": principal.user_id},
    )
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return NotificationUnreadCountResponse(**cached)

    count = await service.unread_count(user_id=principal.user_id)
    payload = NotificationUnreadCountResponse(unread_count=count).model_dump(mode="json")
    await cache.set_json(
        key=cache_key,
        value=jsonable_encoder(payload),
        ttl_seconds=settings.BACKEND_CACHE_NOTIFICATIONS_TTL_SECONDS,
        tags={"notifications", user_tag},
    )
    return NotificationUnreadCountResponse(**payload)


@router.post("/read-all", response_model=NotificationMarkAllReadResponse)
async def mark_notifications_read_all(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("notifications.read")),
    service: NotificationService = Depends(get_notification_service),
):
    result = await service.mark_all_read(user_id=principal.user_id)
    await cache.invalidate_tags("notifications", f"notifications:{principal.user_id}")
    return NotificationMarkAllReadResponse(**result)


@router.post("/{public_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    public_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("notifications.read")),
    service: NotificationService = Depends(get_notification_service),
):
    row = await service.mark_read(
        user_id=principal.user_id,
        notification_public_id=public_id,
    )
    await cache.invalidate_tags("notifications", f"notifications:{principal.user_id}")
    return NotificationResponse(**row)


@router.delete("/{public_id}", response_model=NotificationDeleteResponse)
async def delete_notification(
    public_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("notifications.delete_own")),
    service: NotificationService = Depends(get_notification_service),
):
    row = await service.delete_notification(
        user_id=principal.user_id,
        notification_public_id=public_id,
    )
    await cache.invalidate_tags("notifications", f"notifications:{principal.user_id}")
    return NotificationDeleteResponse(**row)


@router.delete("", response_model=NotificationDeleteResponse)
async def delete_all_notifications(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("notifications.delete_own")),
    service: NotificationService = Depends(get_notification_service),
):
    row = await service.delete_all_notifications(user_id=principal.user_id)
    await cache.invalidate_tags("notifications", f"notifications:{principal.user_id}")
    return NotificationDeleteResponse(**row)


@router.post("/broadcast", response_model=NotificationBroadcastResponse)
async def broadcast_notification(
    payload: NotificationBroadcastRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("notifications.broadcast")),
    service: NotificationService = Depends(get_notification_service),
):
    row = await service.broadcast(
        actor_user_id=principal.user_id,
        event_type=payload.event_type,
        category=payload.category,
        severity=payload.severity,
        title=payload.title,
        body=payload.body,
        entity_type=payload.entity_type,
        entity_public_id=payload.entity_public_id,
        metadata_json=payload.metadata_json,
    )
    await cache.invalidate_tags("notifications")
    return NotificationBroadcastResponse(**row)


@router.post("/send-targeted", response_model=NotificationTargetedSendResponse)
async def send_targeted_notification(
    payload: NotificationTargetedSendRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    _: object = Depends(require_permissions("notifications.send_targeted")),
    service: NotificationService = Depends(get_notification_service),
):
    row = await service.send_targeted(
        actor_user_id=principal.user_id,
        event_type=payload.event_type,
        category=payload.category,
        severity=payload.severity,
        title=payload.title,
        body=payload.body,
        user_ids=payload.user_ids,
        role_ids=payload.role_ids,
        entity_type=payload.entity_type,
        entity_public_id=payload.entity_public_id,
        metadata_json=payload.metadata_json,
    )
    user_tags = {f"notifications:{user_id}" for user_id in row.get("recipient_user_ids", [])}
    await cache.invalidate_tags("notifications", *user_tags)
    return NotificationTargetedSendResponse(**row)
