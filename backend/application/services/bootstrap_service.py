from __future__ import annotations

import logging

from backend.core.config import get_settings
from backend.core.database import get_session
from backend.domain.permissions.catalog import (
    INITIAL_MEMBER_PERMISSION_BUNDLE,
    PERMISSION_CATALOG,
)
from backend.infrastructure.repositories.auth_repository import AuthRepository

logger = logging.getLogger(__name__)


class BootstrapService:
    def __init__(self):
        self.settings = get_settings()

    async def run(self) -> None:
        async with get_session() as session:
            repo = AuthRepository(session)
            await repo.upsert_permissions(permission_catalog=PERMISSION_CATALOG)

            for owner_discord_id in self.settings.owner_discord_ids:
                user = await repo.upsert_user(
                    discord_user_id=owner_discord_id,
                    username=f"Owner-{owner_discord_id}",
                    avatar_hash=None,
                )
                await repo.set_user_permission(
                    user_id=user.id,
                    permission_key="owner.override",
                    allow=True,
                )

            if self.settings.DISCORD_GUILD_ID:
                await repo.ensure_discord_role(
                    guild_id=self.settings.DISCORD_GUILD_ID,
                    discord_role_id=self.settings.BACKEND_INITIAL_MEMBER_ROLE_ID,
                    name="REDACTED",
                    position=0,
                )
                await repo.grant_role_permissions(
                    discord_role_id=self.settings.BACKEND_INITIAL_MEMBER_ROLE_ID,
                    permission_keys=INITIAL_MEMBER_PERMISSION_BUNDLE,
                )

        logger.info("Bootstrap seed completed")
