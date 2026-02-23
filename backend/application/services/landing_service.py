from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.config_registry_repository import (
    ConfigRegistryRepository,
)
from backend.infrastructure.repositories.landing_repository import LandingRepository
from backend.infrastructure.repositories.roster_repository import RosterRepository


class LandingService:
    CURRENT_LEVEL_CONFIG_KEY = "landing.metrics.current_level"
    ONLINE_PLAYERS_CONFIG_KEY = "landing.metrics.online_players"
    DEFAULT_CURRENT_LEVEL = "N/A"
    DEFAULT_ONLINE_PLAYERS = 0

    async def list_posts(
        self,
        *,
        published_only: bool,
        limit: int,
        offset: int,
    ) -> list[dict]:
        async with get_session() as session:
            repo = LandingRepository(session)
            rows = await repo.list_posts(
                published_only=published_only,
                limit=limit,
                offset=offset,
            )
            return [self._post_to_dict(row) for row in rows]


    async def get_post(
        self,
        *,
        public_id: str,
        published_only: bool,
    ) -> dict:
        async with get_session() as session:
            repo = LandingRepository(session)
            row = await repo.get_post_by_public_id(public_id)
            if row is None or (published_only and not row.is_published):
                raise ApiException(
                    status_code=404,
                    error_code="LANDING_POST_NOT_FOUND",
                    message=f"Landing post {public_id} not found",
                )
            return self._post_to_dict(row)

    async def create_post(
        self,
        *,
        title: str,
        content: str,
        media_url: str | None,
        created_by_user_id: int,
    ) -> dict:
        normalized_title = title.strip()
        normalized_content = content.strip()
        normalized_media_url = media_url.strip() if media_url else None
        async with get_session() as session:
            repo = LandingRepository(session)
            row = await repo.create_post(
                public_id=self._public_id(),
                title=normalized_title,
                content=normalized_content,
                media_url=normalized_media_url,
                is_published=False,
                published_at=None,
                created_by_user_id=created_by_user_id,
                updated_by_user_id=created_by_user_id,
            )
            return self._post_to_dict(row)

    async def update_post(
        self,
        *,
        public_id: str,
        title: str | None,
        content: str | None,
        media_url: str | None,
        updated_by_user_id: int,
    ) -> dict:
        async with get_session() as session:
            repo = LandingRepository(session)
            row = await repo.get_post_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="LANDING_POST_NOT_FOUND",
                    message=f"Landing post {public_id} not found",
                )
            if title is not None:
                row.title = title.strip()
            if content is not None:
                row.content = content.strip()
            if media_url is not None:
                row.media_url = media_url.strip() or None
            row.updated_by_user_id = updated_by_user_id
            return self._post_to_dict(row)

    async def set_post_publish_state(
        self,
        *,
        public_id: str,
        is_published: bool,
        updated_by_user_id: int,
    ) -> dict:
        async with get_session() as session:
            repo = LandingRepository(session)
            row = await repo.get_post_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="LANDING_POST_NOT_FOUND",
                    message=f"Landing post {public_id} not found",
                )
            row.is_published = bool(is_published)
            row.updated_by_user_id = updated_by_user_id
            row.published_at = datetime.now(timezone.utc) if row.is_published else None
            return self._post_to_dict(row)

    async def get_public_metrics(self) -> dict:
        async with get_session() as session:
            landing_repo = LandingRepository(session)
            config_repo = ConfigRegistryRepository(session)
            members_count = await landing_repo.count_active_memberships()
            current_level_row = await config_repo.get_by_key(self.CURRENT_LEVEL_CONFIG_KEY)
            online_players_row = await config_repo.get_by_key(self.ONLINE_PLAYERS_CONFIG_KEY)

        current_level = self.DEFAULT_CURRENT_LEVEL
        if current_level_row and isinstance(current_level_row.value_json, (str, int, float)):
            current_level = str(current_level_row.value_json).strip() or self.DEFAULT_CURRENT_LEVEL

        online_players = self.DEFAULT_ONLINE_PLAYERS
        if online_players_row and isinstance(online_players_row.value_json, int):
            online_players = max(0, online_players_row.value_json)

        return {
            "members_count": members_count,
            "current_level": current_level,
            "online_players": online_players,
        }

    async def list_public_roster(self, *, limit: int, offset: int) -> list[dict]:
        async with get_session() as session:
            roster_repo = RosterRepository(session)
            memberships = await roster_repo.list_memberships(
                limit=limit,
                offset=offset,
                status="active",
            )
            result: list[dict] = []
            for membership in memberships:
                player = await roster_repo.get_player_by_id(membership.player_id)
                if player is None:
                    continue
                roster_entry = await roster_repo.get_roster_by_membership_id(membership.id)
                rank_name = None
                if membership.current_rank_id:
                    rank_row = await roster_repo.get_rank_by_id(membership.current_rank_id)
                    rank_name = rank_row.name if rank_row else None
                result.append(
                    {
                        "membership_id": membership.id,
                        "player_id": player.id,
                        "public_player_id": player.public_player_id,
                        "ingame_name": player.ingame_name,
                        "account_name": player.account_name,
                        "rank_name": (roster_entry.display_rank if roster_entry else None)
                        or rank_name,
                        "joined_at": membership.joined_at,
                        "status": membership.status,
                    }
                )
            return result

    @staticmethod
    def _public_id() -> str:
        return f"PST-{uuid4().hex[:12].upper()}"

    @staticmethod
    def _post_to_dict(row) -> dict:
        return {
            "public_id": row.public_id,
            "title": row.title,
            "content": row.content,
            "media_url": row.media_url,
            "is_published": row.is_published,
            "published_at": row.published_at,
            "created_by_user_id": row.created_by_user_id,
            "updated_by_user_id": row.updated_by_user_id,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
