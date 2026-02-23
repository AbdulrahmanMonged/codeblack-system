from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.auth import (
    DiscordRole,
    DiscordRolePermission,
    Permission,
    User,
    UserDiscordRole,
    UserPermission,
    UserSession,
)
from backend.infrastructure.db.models.orders import UserGameAccount


class AuthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_discord_id(self, discord_user_id: int) -> User | None:
        stmt = select(User).where(User.discord_user_id == discord_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_game_account_by_user_id(self, user_id: int) -> UserGameAccount | None:
        stmt = select(UserGameAccount).where(UserGameAccount.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_user(
        self,
        *,
        discord_user_id: int,
        username: str,
        avatar_hash: str | None,
    ) -> User:
        user = await self.get_user_by_discord_id(discord_user_id)
        if user is None:
            user = User(
                discord_user_id=discord_user_id,
                username=username,
                avatar_hash=avatar_hash,
            )
            self.session.add(user)
            await self.session.flush()
            return user

        user.username = username
        user.avatar_hash = avatar_hash
        await self.session.flush()
        return user

    async def touch_user_login(self, user_id: int) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)

    async def upsert_permissions(
        self,
        *,
        permission_catalog: Iterable[tuple[str, str]],
    ) -> None:
        for key, description in permission_catalog:
            stmt = select(Permission).where(Permission.key == key)
            result = await self.session.execute(stmt)
            perm = result.scalar_one_or_none()
            if perm is None:
                self.session.add(Permission(key=key, description=description))
                continue
            perm.description = description
            perm.is_active = True
        await self.session.flush()

    async def upsert_discord_roles(
        self,
        *,
        guild_id: int,
        roles: Sequence[dict[str, int | str]],
    ) -> list[DiscordRole]:
        synced_at = datetime.now(timezone.utc)
        incoming_ids = {int(role["id"]) for role in roles}

        existing_stmt = select(DiscordRole).where(DiscordRole.guild_id == guild_id)
        existing_result = await self.session.execute(existing_stmt)
        existing_roles = {role.discord_role_id: role for role in existing_result.scalars().all()}

        for role in roles:
            role_id = int(role["id"])
            name = str(role.get("name", "unknown"))
            position = int(role.get("position", 0))
            color_int = int(role.get("color_int", role.get("color", 0)) or 0)
            existing = existing_roles.get(role_id)
            if existing is None:
                self.session.add(
                    DiscordRole(
                        discord_role_id=role_id,
                        guild_id=guild_id,
                        name=name,
                        position=position,
                        color_int=color_int,
                        is_active=True,
                        synced_at=synced_at,
                    )
                )
                continue

            existing.name = name
            existing.position = position
            existing.color_int = color_int
            existing.is_active = True
            existing.synced_at = synced_at

        for role_id, role in existing_roles.items():
            if role_id not in incoming_ids:
                role.is_active = False
                role.synced_at = synced_at

        await self.session.flush()

        refreshed_stmt = (
            select(DiscordRole)
            .where(DiscordRole.guild_id == guild_id)
            .order_by(DiscordRole.position.desc())
        )
        refreshed_result = await self.session.execute(refreshed_stmt)
        return refreshed_result.scalars().all()

    async def ensure_discord_role(
        self,
        *,
        guild_id: int,
        discord_role_id: int,
        name: str,
        position: int = 0,
        color_int: int = 0,
    ) -> DiscordRole:
        stmt = select(DiscordRole).where(DiscordRole.discord_role_id == discord_role_id)
        result = await self.session.execute(stmt)
        role = result.scalar_one_or_none()
        if role is None:
            role = DiscordRole(
                discord_role_id=discord_role_id,
                guild_id=guild_id,
                name=name,
                position=position,
                color_int=color_int,
                is_active=True,
                synced_at=datetime.now(timezone.utc),
            )
            self.session.add(role)
            await self.session.flush()
            return role

        role.guild_id = guild_id
        role.name = name
        role.position = position
        role.color_int = color_int
        role.is_active = True
        role.synced_at = datetime.now(timezone.utc)
        await self.session.flush()
        return role

    async def list_discord_roles(self, guild_id: int | None = None) -> Sequence[DiscordRole]:
        stmt = select(DiscordRole).order_by(
            DiscordRole.position.desc(),
            DiscordRole.discord_role_id.asc(),
        )
        if guild_id is not None:
            stmt = stmt.where(DiscordRole.guild_id == guild_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def replace_user_roles(
        self,
        *,
        user_id: int,
        discord_role_ids: Iterable[int],
    ) -> None:
        await self.session.execute(delete(UserDiscordRole).where(UserDiscordRole.user_id == user_id))
        unique_ids = set(int(role_id) for role_id in discord_role_ids)
        for role_id in unique_ids:
            self.session.add(
                UserDiscordRole(
                    user_id=user_id,
                    discord_role_id=role_id,
                )
            )
        await self.session.flush()

    async def list_user_role_ids(self, user_id: int) -> set[int]:
        stmt = select(UserDiscordRole.discord_role_id).where(UserDiscordRole.user_id == user_id)
        result = await self.session.execute(stmt)
        return {int(role_id) for role_id in result.scalars().all()}

    async def replace_role_permissions(
        self,
        *,
        discord_role_id: int,
        permission_keys: Iterable[str],
    ) -> None:
        await self.session.execute(
            delete(DiscordRolePermission).where(
                DiscordRolePermission.discord_role_id == discord_role_id
            )
        )
        for key in set(permission_keys):
            self.session.add(
                DiscordRolePermission(
                    discord_role_id=discord_role_id,
                    permission_key=key,
                )
            )
        await self.session.flush()

    async def grant_role_permissions(
        self,
        *,
        discord_role_id: int,
        permission_keys: Iterable[str],
    ) -> None:
        existing_stmt = select(DiscordRolePermission.permission_key).where(
            DiscordRolePermission.discord_role_id == discord_role_id
        )
        existing_result = await self.session.execute(existing_stmt)
        existing = set(existing_result.scalars().all())

        for key in set(permission_keys):
            if key in existing:
                continue
            self.session.add(
                DiscordRolePermission(
                    discord_role_id=discord_role_id,
                    permission_key=key,
                )
            )
        await self.session.flush()

    async def set_user_permission(
        self,
        *,
        user_id: int,
        permission_key: str,
        allow: bool,
    ) -> None:
        stmt = select(UserPermission).where(
            UserPermission.user_id == user_id,
            UserPermission.permission_key == permission_key,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            self.session.add(
                UserPermission(
                    user_id=user_id,
                    permission_key=permission_key,
                    allow=allow,
                )
            )
        else:
            existing.allow = allow
        await self.session.flush()

    async def list_effective_permission_keys(self, user_id: int) -> set[str]:
        role_stmt = (
            select(DiscordRolePermission.permission_key)
            .join(
                UserDiscordRole,
                UserDiscordRole.discord_role_id == DiscordRolePermission.discord_role_id,
            )
            .where(UserDiscordRole.user_id == user_id)
        )
        role_result = await self.session.execute(role_stmt)
        allowed: set[str] = set(role_result.scalars().all())

        user_stmt = select(UserPermission.permission_key, UserPermission.allow).where(
            UserPermission.user_id == user_id
        )
        user_result = await self.session.execute(user_stmt)
        for key, allow in user_result.all():
            if allow:
                allowed.add(key)
            else:
                allowed.discard(key)
        return allowed

    async def list_permissions(self) -> Sequence[Permission]:
        stmt = select(Permission).where(Permission.is_active == True).order_by(Permission.key.asc())  # noqa: E712
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_active_user_ids_with_any_permissions(
        self,
        *,
        permission_keys: Iterable[str],
    ) -> list[int]:
        target_keys = set(permission_keys)
        if not target_keys:
            return []

        stmt = select(User.id).where(User.is_active == True).order_by(User.id.asc())  # noqa: E712
        result = await self.session.execute(stmt)
        candidate_user_ids = [int(user_id) for user_id in result.scalars().all()]

        matched_user_ids: list[int] = []
        for user_id in candidate_user_ids:
            effective = await self.list_effective_permission_keys(user_id)
            if target_keys.intersection(effective):
                matched_user_ids.append(user_id)
        return matched_user_ids

    async def list_active_user_ids(self, *, user_ids: Iterable[int]) -> list[int]:
        normalized_ids = sorted({int(user_id) for user_id in user_ids})
        if not normalized_ids:
            return []
        stmt = (
            select(User.id)
            .where(
                User.id.in_(normalized_ids),
                User.is_active == True,  # noqa: E712
            )
            .order_by(User.id.asc())
        )
        result = await self.session.execute(stmt)
        return [int(user_id) for user_id in result.scalars().all()]

    async def list_active_user_ids_by_role_ids(
        self,
        *,
        discord_role_ids: Iterable[int],
    ) -> list[int]:
        normalized_role_ids = sorted({int(role_id) for role_id in discord_role_ids})
        if not normalized_role_ids:
            return []
        stmt = (
            select(User.id)
            .join(UserDiscordRole, UserDiscordRole.user_id == User.id)
            .where(
                User.is_active == True,  # noqa: E712
                UserDiscordRole.discord_role_id.in_(normalized_role_ids),
            )
            .distinct()
            .order_by(User.id.asc())
        )
        result = await self.session.execute(stmt)
        return [int(user_id) for user_id in result.scalars().all()]

    async def get_highest_role_color_int(self, *, user_id: int) -> int | None:
        stmt = (
            select(DiscordRole.color_int)
            .join(UserDiscordRole, UserDiscordRole.discord_role_id == DiscordRole.discord_role_id)
            .where(UserDiscordRole.user_id == user_id)
            .order_by(DiscordRole.position.desc(), DiscordRole.discord_role_id.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        if value is None:
            return None
        return int(value)

    async def list_role_permission_pairs(self) -> list[tuple[int, str]]:
        stmt = select(
            DiscordRolePermission.discord_role_id,
            DiscordRolePermission.permission_key,
        )
        result = await self.session.execute(stmt)
        return [(int(role_id), str(permission_key)) for role_id, permission_key in result.all()]

    async def list_existing_permission_keys(self, keys: Iterable[str]) -> set[str]:
        key_set = set(keys)
        if not key_set:
            return set()
        stmt = select(Permission.key).where(Permission.key.in_(key_set))
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    async def create_session(
        self,
        *,
        user_id: int,
        token_jti: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> UserSession:
        session = UserSession(
            user_id=user_id,
            token_jti=token_jti,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
            is_revoked=False,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_session_by_jti(self, token_jti: str) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.token_jti == token_jti)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_session(self, token_jti: str) -> bool:
        stmt = (
            update(UserSession)
            .where(UserSession.token_jti == token_jti, UserSession.is_revoked == False)  # noqa: E712
            .values(
                is_revoked=True,
                revoked_at=datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        return bool(result.rowcount and result.rowcount > 0)
