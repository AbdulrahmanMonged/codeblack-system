"""
Event logging service.
"""

import logging
from datetime import datetime

from bot.core.database import get_session
from bot.core.ipc import IPCManager
from bot.models.event import Event
from bot.repositories.event_repo import EventRepository
from bot.repositories.player_repo import PlayerRepository

logger = logging.getLogger(__name__)


class EventService:

    def __init__(self, ipc: IPCManager | None = None):
        self._ipc = ipc

    async def log_event(
        self,
        timestamp: datetime,
        action_type: str,
        raw_text: str,
        actor_nickname: str | None = None,
        actor_account_name: str | None = None,
        target_nickname: str | None = None,
        target_account_name: str | None = None,
        details: dict | None = None,
        is_system_action: bool = False,
    ) -> Event:
        """Log an event and optionally push to IPC stream."""
        async with get_session() as session:
            player_repo = PlayerRepository(session)
            event_repo = EventRepository(session)

            # Resolve actor player ID
            actor_id = None
            if actor_account_name:
                actor = await player_repo.upsert(
                    actor_account_name, nickname=actor_nickname
                )
                actor_id = actor.id

            # Resolve target player ID
            target_id = None
            if target_account_name:
                target = await player_repo.upsert(
                    target_account_name, nickname=target_nickname
                )
                target_id = target.id

            event = await event_repo.create_event(
                timestamp=timestamp,
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

        # Push to IPC stream for FastAPI
        if self._ipc:
            await self._ipc.push_event(
                "player_event",
                {
                    "action_type": action_type,
                    "actor": actor_account_name,
                    "target": target_account_name,
                    "details": details or {},
                    "timestamp": timestamp.isoformat(),
                },
            )

        return event

    async def get_player_events(
        self, player_id: int, limit: int = 100
    ) -> list[Event]:
        async with get_session() as session:
            repo = EventRepository(session)
            return list(await repo.get_by_player(player_id, limit=limit))

    async def get_recent(self, limit: int = 50) -> list[Event]:
        async with get_session() as session:
            repo = EventRepository(session)
            return list(await repo.get_recent(limit))

    async def get_action_counts(self, player_id: int) -> dict:
        async with get_session() as session:
            repo = EventRepository(session)
            return await repo.get_action_counts(player_id)
