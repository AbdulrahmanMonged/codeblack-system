from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.auth_repository import AuthRepository
from backend.infrastructure.cache.redis_cache import cache
from backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)


class NotificationService:
    DEFAULT_RECIPIENT_PERMISSION = "notifications.read"
    OWNER_OVERRIDE_PERMISSION = "owner.override"

    async def list_notifications(
        self,
        *,
        user_id: int,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> list[dict]:
        async with get_session() as session:
            repo = NotificationRepository(session)
            rows = await repo.list_for_recipient(
                recipient_user_id=user_id,
                unread_only=unread_only,
                limit=limit,
                offset=offset,
            )
            return [
                self._delivery_to_dict(
                    delivery=delivery,
                    notification=notification,
                )
                for delivery, notification in rows
            ]

    async def unread_count(self, *, user_id: int) -> int:
        async with get_session() as session:
            repo = NotificationRepository(session)
            return await repo.unread_count(recipient_user_id=user_id)

    async def mark_read(self, *, user_id: int, notification_public_id: str) -> dict:
        async with get_session() as session:
            repo = NotificationRepository(session)
            row = await repo.mark_read(
                recipient_user_id=user_id,
                notification_public_id=notification_public_id,
            )
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="NOTIFICATION_NOT_FOUND",
                    message=f"Notification {notification_public_id} not found for current user",
                )
            delivery, notification = row
            return self._delivery_to_dict(
                delivery=delivery,
                notification=notification,
            )

    async def mark_all_read(self, *, user_id: int) -> dict:
        async with get_session() as session:
            repo = NotificationRepository(session)
            updated = await repo.mark_all_read(recipient_user_id=user_id)
            return {"updated_count": updated}

    async def delete_notification(
        self,
        *,
        user_id: int,
        notification_public_id: str,
    ) -> dict:
        async with get_session() as session:
            repo = NotificationRepository(session)
            deleted_count = await repo.delete_delivery(
                recipient_user_id=user_id,
                notification_public_id=notification_public_id,
            )
            if deleted_count == 0:
                raise ApiException(
                    status_code=404,
                    error_code="NOTIFICATION_NOT_FOUND",
                    message=f"Notification {notification_public_id} not found for current user",
                )
            return {"deleted_count": deleted_count}

    async def delete_all_notifications(self, *, user_id: int) -> dict:
        async with get_session() as session:
            repo = NotificationRepository(session)
            deleted_count = await repo.delete_all_deliveries(recipient_user_id=user_id)
            return {"deleted_count": deleted_count}

    async def broadcast(
        self,
        *,
        actor_user_id: int,
        event_type: str,
        category: str,
        severity: str,
        title: str,
        body: str,
        entity_type: str | None = None,
        entity_public_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        recipient_permission: str | None = None,
    ) -> dict:
        async with get_session() as session:
            return await self.dispatch_in_session(
                session=session,
                actor_user_id=actor_user_id,
                event_type=event_type,
                category=category,
                severity=severity,
                title=title,
                body=body,
                entity_type=entity_type,
                entity_public_id=entity_public_id,
                metadata_json=metadata_json,
                recipient_permission=recipient_permission,
            )

    async def send_targeted(
        self,
        *,
        actor_user_id: int,
        event_type: str,
        category: str,
        severity: str,
        title: str,
        body: str,
        user_ids: list[int] | None = None,
        role_ids: list[int] | None = None,
        entity_type: str | None = None,
        entity_public_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict:
        normalized_user_ids = {int(user_id) for user_id in (user_ids or [])}
        normalized_role_ids = {int(role_id) for role_id in (role_ids or [])}
        if not normalized_user_ids and not normalized_role_ids:
            raise ApiException(
                status_code=422,
                error_code="NOTIFICATION_TARGETS_REQUIRED",
                message="At least one user_id or role_id must be provided",
            )

        async with get_session() as session:
            auth_repo = AuthRepository(session)
            notification_repo = NotificationRepository(session)

            recipient_user_ids: set[int] = set()
            if normalized_user_ids:
                recipient_user_ids.update(
                    await auth_repo.list_active_user_ids(user_ids=normalized_user_ids)
                )
            if normalized_role_ids:
                recipient_user_ids.update(
                    await auth_repo.list_active_user_ids_by_role_ids(
                        discord_role_ids=normalized_role_ids
                    )
                )

            if not recipient_user_ids:
                raise ApiException(
                    status_code=422,
                    error_code="NOTIFICATION_RECIPIENTS_EMPTY",
                    message="No active recipients matched the provided targets",
                )

            notification = await notification_repo.create_notification(
                public_id=self._public_id(),
                event_type=event_type.strip().lower(),
                category=category.strip().lower(),
                severity=severity.strip().lower(),
                title=title.strip(),
                body=body.strip(),
                entity_type=entity_type.strip().lower() if entity_type else None,
                entity_public_id=entity_public_id.strip() if entity_public_id else None,
                actor_user_id=actor_user_id,
                metadata_json=metadata_json,
            )
            deliveries = await notification_repo.create_deliveries(
                notification_id=notification.id,
                recipient_user_ids=sorted(recipient_user_ids),
            )
            user_tags = {f"notifications:{user_id}" for user_id in recipient_user_ids}
            await cache.invalidate_tags("notifications", *user_tags)
            result = self._notification_to_dict(
                notification=notification,
                recipient_count=len(deliveries),
            )
            result["recipient_user_ids"] = sorted(recipient_user_ids)
            return result

    async def dispatch_in_session(
        self,
        *,
        session: AsyncSession,
        actor_user_id: int | None,
        event_type: str,
        category: str,
        severity: str,
        title: str,
        body: str,
        entity_type: str | None = None,
        entity_public_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        recipient_permission: str | None = None,
    ) -> dict:
        recipient_permission_key = recipient_permission or self.DEFAULT_RECIPIENT_PERMISSION
        auth_repo = AuthRepository(session)
        notification_repo = NotificationRepository(session)

        recipient_user_ids = await auth_repo.list_active_user_ids_with_any_permissions(
            permission_keys={recipient_permission_key, self.OWNER_OVERRIDE_PERMISSION},
        )
        if actor_user_id is not None and actor_user_id not in recipient_user_ids:
            recipient_user_ids.append(actor_user_id)

        notification = await notification_repo.create_notification(
            public_id=self._public_id(),
            event_type=event_type.strip().lower(),
            category=category.strip().lower(),
            severity=severity.strip().lower(),
            title=title.strip(),
            body=body.strip(),
            entity_type=entity_type.strip().lower() if entity_type else None,
            entity_public_id=entity_public_id.strip() if entity_public_id else None,
            actor_user_id=actor_user_id,
            metadata_json=metadata_json,
        )

        deliveries = await notification_repo.create_deliveries(
            notification_id=notification.id,
            recipient_user_ids=sorted(set(recipient_user_ids)),
        )
        user_tags = {f"notifications:{user_id}" for user_id in recipient_user_ids}
        await cache.invalidate_tags("notifications", *user_tags)
        return self._notification_to_dict(
            notification=notification,
            recipient_count=len(deliveries),
        )

    @staticmethod
    def _public_id() -> str:
        return f"NTF-{uuid4().hex[:14].upper()}"

    @staticmethod
    def _notification_to_dict(
        *,
        notification,
        recipient_count: int,
    ) -> dict:
        return {
            "public_id": notification.public_id,
            "event_type": notification.event_type,
            "category": notification.category,
            "severity": notification.severity,
            "title": notification.title,
            "body": notification.body,
            "entity_type": notification.entity_type,
            "entity_public_id": notification.entity_public_id,
            "actor_user_id": notification.actor_user_id,
            "metadata_json": notification.metadata_json,
            "created_at": notification.created_at,
            "recipient_count": recipient_count,
        }

    @staticmethod
    def _delivery_to_dict(
        *,
        delivery,
        notification,
    ) -> dict:
        return {
            "public_id": notification.public_id,
            "event_type": notification.event_type,
            "category": notification.category,
            "severity": notification.severity,
            "title": notification.title,
            "body": notification.body,
            "entity_type": notification.entity_type,
            "entity_public_id": notification.entity_public_id,
            "actor_user_id": notification.actor_user_id,
            "metadata_json": notification.metadata_json,
            "created_at": notification.created_at,
            "is_read": delivery.is_read,
            "read_at": delivery.read_at,
        }
