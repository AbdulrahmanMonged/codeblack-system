from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.notifications import (
    Notification,
    NotificationDelivery,
)


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_notification(
        self,
        *,
        public_id: str,
        event_type: str,
        category: str,
        severity: str,
        title: str,
        body: str,
        entity_type: str | None,
        entity_public_id: str | None,
        actor_user_id: int | None,
        metadata_json: dict | None,
    ) -> Notification:
        row = Notification(
            public_id=public_id,
            event_type=event_type,
            category=category,
            severity=severity,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_public_id=entity_public_id,
            actor_user_id=actor_user_id,
            metadata_json=metadata_json,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_deliveries(
        self,
        *,
        notification_id: int,
        recipient_user_ids: Sequence[int],
    ) -> list[NotificationDelivery]:
        rows: list[NotificationDelivery] = []
        for user_id in recipient_user_ids:
            row = NotificationDelivery(
                notification_id=notification_id,
                recipient_user_id=user_id,
                is_read=False,
                read_at=None,
            )
            self.session.add(row)
            rows.append(row)
        await self.session.flush()
        return rows

    async def list_for_recipient(
        self,
        *,
        recipient_user_id: int,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> Sequence[tuple[NotificationDelivery, Notification]]:
        stmt = (
            select(NotificationDelivery, Notification)
            .join(Notification, Notification.id == NotificationDelivery.notification_id)
            .where(NotificationDelivery.recipient_user_id == recipient_user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if unread_only:
            stmt = stmt.where(NotificationDelivery.is_read == False)  # noqa: E712
        result = await self.session.execute(stmt)
        return result.all()

    async def get_delivery_by_public_id(
        self,
        *,
        recipient_user_id: int,
        notification_public_id: str,
    ) -> tuple[NotificationDelivery, Notification] | None:
        stmt = (
            select(NotificationDelivery, Notification)
            .join(Notification, Notification.id == NotificationDelivery.notification_id)
            .where(
                NotificationDelivery.recipient_user_id == recipient_user_id,
                Notification.public_id == notification_public_id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return row

    async def mark_read(
        self,
        *,
        recipient_user_id: int,
        notification_public_id: str,
    ) -> tuple[NotificationDelivery, Notification] | None:
        row = await self.get_delivery_by_public_id(
            recipient_user_id=recipient_user_id,
            notification_public_id=notification_public_id,
        )
        if row is None:
            return None
        delivery, notification = row
        if not delivery.is_read:
            delivery.is_read = True
            delivery.read_at = datetime.now(timezone.utc)
            await self.session.flush()
        return delivery, notification

    async def mark_all_read(self, *, recipient_user_id: int) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(NotificationDelivery)
            .where(
                NotificationDelivery.recipient_user_id == recipient_user_id,
                NotificationDelivery.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=now)
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def unread_count(self, *, recipient_user_id: int) -> int:
        stmt = (
            select(func.count(NotificationDelivery.id))
            .where(
                NotificationDelivery.recipient_user_id == recipient_user_id,
                NotificationDelivery.is_read == False,  # noqa: E712
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def delete_delivery(
        self,
        *,
        recipient_user_id: int,
        notification_public_id: str,
    ) -> int:
        stmt = (
            delete(NotificationDelivery)
            .where(
                NotificationDelivery.id.in_(
                    select(NotificationDelivery.id)
                    .join(Notification, Notification.id == NotificationDelivery.notification_id)
                    .where(
                        NotificationDelivery.recipient_user_id == recipient_user_id,
                        Notification.public_id == notification_public_id,
                    )
                )
            )
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def delete_all_deliveries(self, *, recipient_user_id: int) -> int:
        stmt = delete(NotificationDelivery).where(
            NotificationDelivery.recipient_user_id == recipient_user_id
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
