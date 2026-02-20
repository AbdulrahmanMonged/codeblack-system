from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.audit import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str | None,
        action: str,
        actor_user_id: int | None,
        request_id: str | None,
        details_json: dict[str, Any] | None,
    ) -> AuditEvent:
        row = AuditEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_user_id=actor_user_id,
            request_id=request_id,
            details_json=details_json,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_events(
        self,
        *,
        limit: int,
        offset: int,
        event_type: str | None = None,
        actor_user_id: int | None = None,
    ) -> Sequence[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if actor_user_id is not None:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()
