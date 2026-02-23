from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.orders import Order, OrderReview, UserGameAccount


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_user_game_account(
        self,
        *,
        user_id: int,
        discord_user_id: int,
        account_name: str,
        is_verified: bool,
        mta_serial: str | None = None,
        forum_url: str | None = None,
        verified_at=None,
        verified_by_user_id: int | None = None,
    ) -> UserGameAccount:
        row = await self.get_user_game_account_by_discord(discord_user_id)
        if row is None:
            row = UserGameAccount(
                user_id=user_id,
                discord_user_id=discord_user_id,
                account_name=account_name,
                is_verified=is_verified,
                mta_serial=mta_serial,
                forum_url=forum_url,
                verified_at=verified_at,
                verified_by_user_id=verified_by_user_id,
            )
            self.session.add(row)
            await self.session.flush()
            return row

        row.user_id = user_id
        row.account_name = account_name
        row.is_verified = is_verified
        row.mta_serial = mta_serial
        row.forum_url = forum_url
        row.verified_at = verified_at
        row.verified_by_user_id = verified_by_user_id
        await self.session.flush()
        return row

    async def get_user_game_account_by_discord(self, discord_user_id: int) -> UserGameAccount | None:
        stmt = select(UserGameAccount).where(UserGameAccount.discord_user_id == discord_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_game_account_by_account_name(self, account_name: str) -> UserGameAccount | None:
        stmt = select(UserGameAccount).where(UserGameAccount.account_name == account_name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_game_account_by_user(self, user_id: int) -> UserGameAccount | None:
        stmt = select(UserGameAccount).where(UserGameAccount.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_order(self, **kwargs) -> Order:
        row = Order(**kwargs)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_order_by_public_id(self, public_id: str) -> Order | None:
        stmt = select(Order).where(Order.public_id == public_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_orders(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[Order]:
        stmt = select(Order).order_by(Order.submitted_at.desc())
        if status:
            stmt = stmt.where(Order.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_orders_by_submitter(
        self,
        *,
        submitted_by_user_id: int,
        status: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[Order]:
        stmt = (
            select(Order)
            .where(Order.submitted_by_user_id == submitted_by_user_id)
            .order_by(Order.submitted_at.desc())
        )
        if status:
            stmt = stmt.where(Order.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_order_review(
        self,
        *,
        order_id: int,
        reviewer_user_id: int,
        decision: str,
        reason: str | None,
    ) -> OrderReview:
        row = OrderReview(
            order_id=order_id,
            reviewer_user_id=reviewer_user_id,
            decision=decision,
            reason=reason,
        )
        self.session.add(row)
        await self.session.flush()
        return row
