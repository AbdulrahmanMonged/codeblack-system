from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.vacations import VacationRequest


class VacationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_request(self, **kwargs) -> VacationRequest:
        row = VacationRequest(**kwargs)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_by_public_id(self, public_id: str) -> VacationRequest | None:
        stmt = select(VacationRequest).where(VacationRequest.public_id == public_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        *,
        status: str | None,
        player_id: int | None,
        limit: int,
        offset: int,
    ) -> Sequence[VacationRequest]:
        stmt = select(VacationRequest).order_by(VacationRequest.created_at.desc())
        if status:
            stmt = stmt.where(VacationRequest.status == status)
        if player_id is not None:
            stmt = stmt.where(VacationRequest.player_id == player_id)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def review_request(
        self,
        *,
        public_id: str,
        reviewer_user_id: int,
        status: str,
        review_comment: str | None,
    ) -> VacationRequest | None:
        row = await self.get_by_public_id(public_id)
        if row is None:
            return None
        row.status = status
        row.reviewed_by_user_id = reviewer_user_id
        row.review_comment = review_comment
        row.reviewed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return row
