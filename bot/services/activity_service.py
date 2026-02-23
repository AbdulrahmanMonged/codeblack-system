"""
Player activity tracking service.
"""

import logging
from datetime import datetime

from bot.core.database import get_session
from bot.core.ipc import IPCManager
from bot.models.activity import PlayerActivity
from bot.repositories.activity_repo import ActivityRepository
from bot.repositories.player_repo import PlayerRepository

logger = logging.getLogger(__name__)


class ActivityService:

    def __init__(self, ipc: IPCManager | None = None):
        self._ipc = ipc

    async def record_login(
        self,
        account_name: str,
        nickname: str,
        login_time: datetime | None = None,
        metadata: dict | None = None,
    ) -> PlayerActivity:
        """Record a player login event."""
        if login_time is None:
            login_time = datetime.utcnow()

        async with get_session() as session:
            player_repo = PlayerRepository(session)
            activity_repo = ActivityRepository(session)

            player = await player_repo.upsert(
                account_name, nickname=nickname, last_online=login_time
            )

            activity = await activity_repo.create_session(
                account_name=account_name,
                nickname=nickname,
                login_time=login_time,
                player_id=player.id,
                metadata=metadata,
            )

        if self._ipc:
            await self._ipc.publish_event(
                "player_login",
                {"player": account_name, "nickname": nickname},
            )

        return activity

    async def record_logout(
        self,
        account_name: str,
        logout_time: datetime | None = None,
    ) -> PlayerActivity | None:
        """Record a player logout event."""
        if logout_time is None:
            logout_time = datetime.utcnow()

        async with get_session() as session:
            repo = ActivityRepository(session)
            activity = await repo.end_session(account_name, logout_time)

        if activity and self._ipc:
            await self._ipc.publish_event(
                "player_logout",
                {
                    "player": account_name,
                    "duration_seconds": activity.session_duration,
                },
            )

        return activity

    async def get_active_sessions(self) -> list[PlayerActivity]:
        async with get_session() as session:
            repo = ActivityRepository(session)
            return list(await repo.get_active_sessions())

    async def get_player_total(
        self, account_name: str, month: str | None = None
    ) -> dict:
        async with get_session() as session:
            repo = ActivityRepository(session)
            return await repo.get_player_total(account_name, month)

    async def get_all_players_summary(
        self, month: str | None = None
    ) -> list[dict]:
        async with get_session() as session:
            repo = ActivityRepository(session)
            return await repo.get_all_players_summary(month)

    async def get_player_sessions(
        self, account_name: str, month: str | None = None, limit: int = 50
    ) -> list[PlayerActivity]:
        async with get_session() as session:
            repo = ActivityRepository(session)
            return list(
                await repo.get_player_sessions(account_name, month, limit)
            )

    async def get_monthly_stats(self, month: str) -> dict:
        async with get_session() as session:
            repo = ActivityRepository(session)
            return await repo.get_monthly_stats(month)

    async def get_inactive_players(self, days_threshold: int = 7) -> list[dict]:
        async with get_session() as session:
            repo = ActivityRepository(session)
            return await repo.get_inactive_players(days_threshold)
