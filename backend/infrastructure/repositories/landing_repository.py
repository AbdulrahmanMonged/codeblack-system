from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.portal import LandingPost
from backend.infrastructure.db.models.roster import GroupMembership


class LandingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_post(self, **kwargs) -> LandingPost:
        row = LandingPost(**kwargs)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_post_by_public_id(self, public_id: str) -> LandingPost | None:
        stmt = select(LandingPost).where(LandingPost.public_id == public_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_posts(
        self,
        *,
        published_only: bool,
        limit: int,
        offset: int,
    ) -> Sequence[LandingPost]:
        stmt = select(LandingPost).order_by(
            LandingPost.published_at.desc().nullslast(),
            LandingPost.created_at.desc(),
        )
        if published_only:
            stmt = stmt.where(LandingPost.is_published == True)  # noqa: E712
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_active_memberships(self) -> int:
        stmt = select(func.count(GroupMembership.id)).where(
            GroupMembership.status == "active"
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)
