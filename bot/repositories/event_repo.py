from datetime import date, datetime
from typing import Sequence

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.event import Event
from bot.models.player import Player
from .base import BaseRepository


class EventRepository(BaseRepository[Event]):

    def __init__(self, session: AsyncSession):
        super().__init__(session, Event)

    async def create_event(
        self,
        timestamp: datetime,
        action_type: str,
        raw_text: str,
        actor_id: int | None = None,
        actor_nickname: str | None = None,
        actor_account_name: str | None = None,
        target_id: int | None = None,
        target_nickname: str | None = None,
        target_account_name: str | None = None,
        details: dict | None = None,
        is_system_action: bool = False,
    ) -> Event:
        return await self.create(
            timestamp=timestamp,
            date=timestamp.date(),
            time=timestamp.time(),
            action_type=action_type,
            raw_text=raw_text,
            actor_id=actor_id,
            actor_nickname=actor_nickname,
            actor_account_name=actor_account_name,
            target_id=target_id,
            target_nickname=target_nickname,
            target_account_name=target_account_name,
            details=details,
            is_system_action=is_system_action,
        )

    async def get_by_player(
        self,
        player_id: int,
        as_actor: bool | None = None,
        as_target: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Event]:
        stmt = select(Event)

        if as_actor and not as_target:
            stmt = stmt.where(Event.actor_id == player_id)
        elif as_target and not as_actor:
            stmt = stmt.where(Event.target_id == player_id)
        else:
            stmt = stmt.where(
                or_(Event.actor_id == player_id, Event.target_id == player_id)
            )

        stmt = stmt.order_by(Event.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_type(
        self, action_type: str, limit: int = 100, offset: int = 0
    ) -> Sequence[Event]:
        stmt = (
            select(Event)
            .where(Event.action_type == action_type)
            .order_by(Event.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_date_range(
        self, start: date, end: date, limit: int = 1000
    ) -> Sequence[Event]:
        stmt = (
            select(Event)
            .where(Event.date.between(start, end))
            .order_by(Event.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_recent(self, limit: int = 50) -> Sequence[Event]:
        stmt = select(Event).order_by(Event.timestamp.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_action_counts(self, player_id: int) -> dict:
        """Get grouped action counts for a player as actor and target."""
        actor_stmt = (
            select(Event.action_type, func.count().label("count"))
            .where(Event.actor_id == player_id)
            .group_by(Event.action_type)
        )
        target_stmt = (
            select(Event.action_type, func.count().label("count"))
            .where(Event.target_id == player_id)
            .group_by(Event.action_type)
        )

        actor_result = await self.session.execute(actor_stmt)
        target_result = await self.session.execute(target_stmt)

        actor_counts = {row.action_type: row.count for row in actor_result}
        target_counts = {row.action_type: row.count for row in target_result}

        return {
            "as_actor": sum(actor_counts.values()),
            "as_target": sum(target_counts.values()),
            "total": sum(actor_counts.values()) + sum(target_counts.values()),
            "as_actor_by_type": actor_counts,
            "as_target_by_type": target_counts,
        }
