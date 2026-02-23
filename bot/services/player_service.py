"""
Player business logic service.
"""

import logging
from datetime import datetime

from bot.core.database import get_session
from bot.core.redis import RedisManager
from bot.models.player import Player
from bot.repositories.player_repo import PlayerRepository

logger = logging.getLogger(__name__)

# Redis cache prefix for player lookups
CACHE_PREFIX = "REDACTED:cache:player"
CACHE_TTL = 3600  # 1 hour


class PlayerService:

    async def get_or_create(self, account_name: str, **kwargs) -> Player:
        async with get_session() as session:
            repo = PlayerRepository(session)
            return await repo.upsert(account_name, **kwargs)

    async def get_by_account_name(self, account_name: str) -> Player | None:
        async with get_session() as session:
            repo = PlayerRepository(session)
            return await repo.get_by_account_name(account_name)

    async def get_by_nickname(self, nickname: str) -> Player | None:
        async with get_session() as session:
            repo = PlayerRepository(session)
            return await repo.get_by_nickname(nickname)

    async def get_by_discord_id(self, discord_id: int) -> Player | None:
        async with get_session() as session:
            repo = PlayerRepository(session)
            return await repo.get_by_discord_id(discord_id)

    async def resolve_account_name(self, nickname: str) -> str | None:
        """
        Multi-tier resolution: Redis cache → DB → None.
        Used by ActivityMonitor for fast nickname → account_name lookups.
        """
        cache_key = f"{CACHE_PREFIX}:nick:{nickname.lower()}"

        # Tier 1: Redis cache
        cached = await RedisManager.get(cache_key)
        if cached:
            return cached

        # Tier 2: Database
        async with get_session() as session:
            repo = PlayerRepository(session)
            account_name = await repo.get_account_name_by_nickname(nickname)

        if account_name:
            await RedisManager.set(cache_key, account_name, expire=CACHE_TTL)
            return account_name

        return None

    async def cache_nickname_mapping(
        self, nickname: str, account_name: str
    ) -> None:
        """Explicitly cache a nickname → account_name mapping."""
        cache_key = f"{CACHE_PREFIX}:nick:{nickname.lower()}"
        await RedisManager.set(cache_key, account_name, expire=CACHE_TTL)

    async def update_rank(self, account_name: str, new_rank: str) -> Player | None:
        async with get_session() as session:
            repo = PlayerRepository(session)
            player = await repo.get_by_account_name(account_name)
            if player:
                return await repo.update(
                    player, rank=new_rank, last_rank_change=datetime.utcnow()
                )
            return None

    async def mark_left_group(self, account_name: str) -> bool:
        async with get_session() as session:
            repo = PlayerRepository(session)
            player = await repo.get_by_account_name(account_name)
            if player:
                await repo.update(player, is_in_group=False)
                return True
            return False

    async def mark_joined_group(self, account_name: str) -> bool:
        async with get_session() as session:
            repo = PlayerRepository(session)
            player = await repo.get_by_account_name(account_name)
            if player:
                await repo.update(player, is_in_group=True)
                return True
            return False

    async def get_all_in_group(self) -> list[Player]:
        async with get_session() as session:
            repo = PlayerRepository(session)
            return list(await repo.get_in_group())

    async def get_blacklisted(self) -> list[Player]:
        async with get_session() as session:
            repo = PlayerRepository(session)
            return list(await repo.get_blacklisted())

    async def set_blacklisted(self, account_name: str, blacklisted: bool) -> bool:
        async with get_session() as session:
            repo = PlayerRepository(session)
            player = await repo.get_by_account_name(account_name)
            if player:
                await repo.update(player, is_blacklisted=blacklisted)
                return True
            return False

    async def update_warning_level(
        self, account_name: str, warning_level: int
    ) -> bool:
        async with get_session() as session:
            repo = PlayerRepository(session)
            player = await repo.get_by_account_name(account_name)
            if player:
                await repo.update(player, warning_level=warning_level)
                return True
            return False
