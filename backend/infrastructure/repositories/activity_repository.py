from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.activities import ActivityParticipant, GroupActivity


class ActivityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_activity(self, **kwargs) -> GroupActivity:
        row = GroupActivity(**kwargs)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_by_public_id(self, public_id: str) -> GroupActivity | None:
        stmt = select(GroupActivity).where(GroupActivity.public_id == public_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_activities(
        self,
        *,
        status: str | None,
        activity_type: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[GroupActivity]:
        stmt = select(GroupActivity).order_by(GroupActivity.created_at.desc())
        if status:
            stmt = stmt.where(GroupActivity.status == status)
        if activity_type:
            stmt = stmt.where(GroupActivity.activity_type == activity_type)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_due_scheduled_for_publish(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> Sequence[GroupActivity]:
        stmt = (
            select(GroupActivity)
            .where(
                GroupActivity.status == "scheduled",
                GroupActivity.scheduled_for.is_not(None),
                GroupActivity.scheduled_for <= now,
            )
            .order_by(GroupActivity.scheduled_for.asc(), GroupActivity.id.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_retryable_publish_failures(
        self,
        *,
        retry_before: datetime,
        max_attempts: int,
        limit: int,
    ) -> Sequence[GroupActivity]:
        stmt = (
            select(GroupActivity)
            .where(
                GroupActivity.status == "publish_failed",
                GroupActivity.publish_attempts < max_attempts,
                (
                    GroupActivity.last_publish_attempt_at.is_(None)
                    | (GroupActivity.last_publish_attempt_at <= retry_before)
                ),
            )
            .order_by(GroupActivity.last_publish_attempt_at.asc().nullsfirst(), GroupActivity.id.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_participant(
        self,
        *,
        activity_id: int,
        player_id: int,
        participant_role: str,
        attendance_status: str,
        notes: str | None,
    ) -> ActivityParticipant:
        row = ActivityParticipant(
            activity_id=activity_id,
            player_id=player_id,
            participant_role=participant_role,
            attendance_status=attendance_status,
            notes=notes,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_participants(self, activity_id: int) -> Sequence[ActivityParticipant]:
        stmt = select(ActivityParticipant).where(ActivityParticipant.activity_id == activity_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
