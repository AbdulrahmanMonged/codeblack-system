from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.player import Player
from .base import BaseRepository


class PlayerRepository(BaseRepository[Player]):

    def __init__(self, session: AsyncSession):
        super().__init__(session, Player)

    async def get_by_account_name(self, account_name: str) -> Player | None:
        stmt = select(Player).where(Player.account_name == account_name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_nickname(self, nickname: str) -> Player | None:
        stmt = select(Player).where(
            func.lower(Player.nickname) == func.lower(nickname)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_discord_id(self, discord_id: int) -> Player | None:
        stmt = select(Player).where(Player.discord_id == discord_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, account_name: str, **kwargs) -> Player:
        """Create player if not exists, otherwise update non-None fields."""
        player = await self.get_by_account_name(account_name)
        if player:
            return await self.update(player, **kwargs)
        return await self.create(account_name=account_name, **kwargs)

    async def get_in_group(self) -> Sequence[Player]:
        stmt = (
            select(Player)
            .where(Player.is_in_group == True)  # noqa: E712
            .order_by(Player.account_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_not_in_group(self) -> Sequence[Player]:
        stmt = (
            select(Player)
            .where(Player.is_in_group == False)  # noqa: E712
            .order_by(Player.account_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_blacklisted(self) -> Sequence[Player]:
        stmt = (
            select(Player)
            .where(Player.is_blacklisted == True)  # noqa: E712
            .order_by(Player.account_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_account_name_by_nickname(self, nickname: str) -> str | None:
        stmt = select(Player.account_name).where(
            func.lower(Player.nickname) == func.lower(nickname)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
