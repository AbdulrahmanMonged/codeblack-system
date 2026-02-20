from datetime import datetime
from typing import Sequence

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.activity import PlayerActivity
from bot.models.player import Player
from .base import BaseRepository


class ActivityRepository(BaseRepository[PlayerActivity]):

    def __init__(self, session: AsyncSession):
        super().__init__(session, PlayerActivity)

    async def create_session(
        self,
        account_name: str,
        nickname: str,
        login_time: datetime,
        player_id: int | None = None,
        metadata: dict | None = None,
    ) -> PlayerActivity:
        return await self.create(
            account_name=account_name,
            nickname=nickname,
            login_time=login_time,
            date=login_time.date(),
            month=login_time.strftime("%Y-%m"),
            year=login_time.year,
            player_id=player_id,
            metadata_=metadata,
        )

    async def end_session(
        self, account_name: str, logout_time: datetime
    ) -> PlayerActivity | None:
        """End the most recent open session for a player."""
        stmt = (
            select(PlayerActivity)
            .where(
                PlayerActivity.account_name == account_name,
                PlayerActivity.logout_time.is_(None),
            )
            .order_by(PlayerActivity.login_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()

        if session is None:
            return None

        duration = int((logout_time - session.login_time).total_seconds())
        session.logout_time = logout_time
        session.session_duration = duration
        await self.session.flush()
        return session

    async def get_active_sessions(self) -> Sequence[PlayerActivity]:
        stmt = (
            select(PlayerActivity)
            .where(PlayerActivity.logout_time.is_(None))
            .order_by(PlayerActivity.login_time.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_player_total(
        self, account_name: str, month: str | None = None
    ) -> dict:
        stmt = select(
            func.coalesce(func.sum(PlayerActivity.session_duration), 0).label(
                "total_seconds"
            ),
            func.count().label("session_count"),
        ).where(
            PlayerActivity.account_name == account_name,
            PlayerActivity.session_duration.isnot(None),
        )

        if month:
            stmt = stmt.where(PlayerActivity.month == month)

        result = await self.session.execute(stmt)
        row = result.one()

        total = row.total_seconds
        count = row.session_count

        return {
            "account_name": account_name,
            "total_seconds": total,
            "total_hours": round(total / 3600, 2),
            "total_days": round(total / 86400, 2),
            "session_count": count,
            "average_session_seconds": total // count if count > 0 else 0,
            "month": month,
        }

    async def get_all_players_summary(
        self, month: str | None = None
    ) -> list[dict]:
        stmt = (
            select(
                PlayerActivity.account_name,
                PlayerActivity.nickname,
                Player.rank,
                func.coalesce(func.sum(PlayerActivity.session_duration), 0).label(
                    "total_seconds"
                ),
                func.count().label("session_count"),
                func.min(PlayerActivity.login_time).label("first_session"),
                func.max(PlayerActivity.login_time).label("last_session"),
            )
            .outerjoin(Player, PlayerActivity.player_id == Player.id)
            .where(PlayerActivity.session_duration.isnot(None))
            .group_by(PlayerActivity.account_name, PlayerActivity.nickname, Player.rank)
            .order_by(text("total_seconds DESC"))
        )

        if month:
            stmt = stmt.where(PlayerActivity.month == month)

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "account_name": r.account_name,
                "nickname": r.nickname,
                "rank": r.rank,
                "total_seconds": r.total_seconds,
                "total_hours": round(r.total_seconds / 3600, 2),
                "total_days": round(r.total_seconds / 86400, 2),
                "session_count": r.session_count,
                "first_session": r.first_session,
                "last_session": r.last_session,
                "month": month,
            }
            for r in rows
        ]

    async def get_player_sessions(
        self, account_name: str, month: str | None = None, limit: int = 50
    ) -> Sequence[PlayerActivity]:
        stmt = (
            select(PlayerActivity)
            .where(PlayerActivity.account_name == account_name)
            .order_by(PlayerActivity.login_time.desc())
            .limit(limit)
        )
        if month:
            stmt = stmt.where(PlayerActivity.month == month)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_inactive_players(
        self, days_threshold: int = 7
    ) -> list[dict]:
        stmt = (
            select(
                Player.account_name,
                Player.nickname,
                Player.rank,
                Player.last_online,
                func.max(PlayerActivity.logout_time).label("last_activity"),
            )
            .outerjoin(PlayerActivity, Player.id == PlayerActivity.player_id)
            .where(Player.is_in_group == True)  # noqa: E712
            .group_by(
                Player.id,
                Player.account_name,
                Player.nickname,
                Player.rank,
                Player.last_online,
            )
            .having(
                func.max(PlayerActivity.logout_time).is_(None)
                | (
                    func.max(PlayerActivity.logout_time)
                    < func.now() - text(f"INTERVAL '{days_threshold} days'")
                )
            )
            .order_by(text("last_activity DESC NULLS LAST"))
        )

        result = await self.session.execute(stmt)
        return [row._asdict() for row in result.all()]

    async def get_monthly_stats(self, month: str) -> dict:
        stmt = select(
            func.count(func.distinct(PlayerActivity.account_name)).label(
                "unique_players"
            ),
            func.count().label("total_sessions"),
            func.coalesce(func.sum(PlayerActivity.session_duration), 0).label(
                "total_seconds"
            ),
            func.coalesce(func.avg(PlayerActivity.session_duration), 0).label(
                "avg_session"
            ),
            func.min(PlayerActivity.login_time).label("first_login"),
            func.max(PlayerActivity.logout_time).label("last_logout"),
        ).where(
            PlayerActivity.month == month,
            PlayerActivity.session_duration.isnot(None),
        )

        result = await self.session.execute(stmt)
        row = result.one()

        total = row.total_seconds
        avg_sec = float(row.avg_session or 0)

        return {
            "month": month,
            "unique_players": row.unique_players or 0,
            "total_sessions": row.total_sessions or 0,
            "total_hours": round(total / 3600, 2),
            "total_days": round(total / 86400, 2),
            "average_session_seconds": int(avg_sec),
            "average_session_hours": round(avg_sec / 3600, 2),
            "first_login": row.first_login,
            "last_logout": row.last_logout,
        }
