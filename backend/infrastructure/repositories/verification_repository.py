from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.portal import VerificationRequest


class VerificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_request(self, **kwargs) -> VerificationRequest:
        row = VerificationRequest(**kwargs)
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_public_id(self, public_id: str) -> VerificationRequest | None:
        stmt = select(VerificationRequest).where(VerificationRequest.public_id == public_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_user(self, *, user_id: int) -> VerificationRequest | None:
        stmt = (
            select(VerificationRequest)
            .where(VerificationRequest.user_id == user_id)
            .order_by(VerificationRequest.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[VerificationRequest]:
        stmt = select(VerificationRequest).order_by(VerificationRequest.created_at.desc())
        if status:
            stmt = stmt.where(VerificationRequest.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_pending_for_user(self, *, user_id: int) -> Sequence[VerificationRequest]:
        stmt = select(VerificationRequest).where(
            VerificationRequest.user_id == user_id,
            VerificationRequest.status == "pending",
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def set_review_decision(
        self,
        *,
        row: VerificationRequest,
        status: str,
        review_comment: str | None,
        reviewed_by_user_id: int,
    ) -> VerificationRequest:
        row.status = status
        row.review_comment = review_comment
        row.reviewed_by_user_id = reviewed_by_user_id
        row.reviewed_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(row)
        return row
