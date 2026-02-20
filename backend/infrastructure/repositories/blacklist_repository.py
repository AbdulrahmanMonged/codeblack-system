from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.blacklist import (
    BlacklistEntry,
    BlacklistHistory,
    BlacklistRemovalRequest,
)


class BlacklistRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_next_sequence(self) -> int:
        stmt = select(func.max(BlacklistEntry.blacklist_sequence))
        result = await self.session.execute(stmt)
        max_value = result.scalar()
        return int(max_value or 0) + 1

    async def create_entry(self, **kwargs) -> BlacklistEntry:
        row = BlacklistEntry(**kwargs)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_entry_by_id(self, entry_id: int) -> BlacklistEntry | None:
        stmt = select(BlacklistEntry).where(BlacklistEntry.id == entry_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_entries(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[BlacklistEntry]:
        stmt = select(BlacklistEntry).order_by(BlacklistEntry.id.desc())
        if status:
            stmt = stmt.where(BlacklistEntry.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_active_by_account_name(self, account_name: str) -> BlacklistEntry | None:
        stmt = select(BlacklistEntry).where(
            BlacklistEntry.identity == account_name,
            BlacklistEntry.status == "active",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_history(
        self,
        *,
        blacklist_entry_id: int,
        action: str,
        actor_user_id: int,
        change_set: str,
    ) -> BlacklistHistory:
        row = BlacklistHistory(
            blacklist_entry_id=blacklist_entry_id,
            action=action,
            actor_user_id=actor_user_id,
            change_set=change_set,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_removal_request(self, **kwargs) -> BlacklistRemovalRequest:
        row = BlacklistRemovalRequest(**kwargs)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_pending_removal_request_by_account(
        self,
        *,
        account_name: str,
    ) -> BlacklistRemovalRequest | None:
        stmt = select(BlacklistRemovalRequest).where(
            BlacklistRemovalRequest.account_name == account_name,
            BlacklistRemovalRequest.status == "pending",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_removal_requests(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[BlacklistRemovalRequest]:
        stmt = select(BlacklistRemovalRequest).order_by(
            BlacklistRemovalRequest.requested_at.desc()
        )
        if status:
            stmt = stmt.where(BlacklistRemovalRequest.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_removal_requests_by_account(
        self,
        *,
        account_name: str,
        limit: int,
    ) -> Sequence[BlacklistRemovalRequest]:
        stmt = (
            select(BlacklistRemovalRequest)
            .where(BlacklistRemovalRequest.account_name == account_name)
            .order_by(BlacklistRemovalRequest.requested_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_removal_request_by_id(self, request_id: int) -> BlacklistRemovalRequest | None:
        stmt = select(BlacklistRemovalRequest).where(BlacklistRemovalRequest.id == request_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def review_removal_request(
        self,
        *,
        request_id: int,
        reviewer_user_id: int,
        status: str,
        review_comment: str | None,
    ) -> BlacklistRemovalRequest | None:
        row = await self.get_removal_request_by_id(request_id)
        if row is None:
            return None
        row.status = status
        row.review_comment = review_comment
        row.reviewed_by_user_id = reviewer_user_id
        row.reviewed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return row
