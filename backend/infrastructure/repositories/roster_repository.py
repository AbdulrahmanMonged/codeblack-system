from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.roster import (
    GroupMembership,
    GroupRank,
    GroupRoster,
    PlayerPunishment,
    Playerbase,
)


class RosterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_rank(
        self,
        *,
        name: str,
        level: int,
    ) -> GroupRank:
        row = GroupRank(name=name, level=level, is_active=True)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_ranks(self) -> Sequence[GroupRank]:
        stmt = select(GroupRank).order_by(GroupRank.level.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_rank_by_id(self, rank_id: int) -> GroupRank | None:
        stmt = select(GroupRank).where(GroupRank.id == rank_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_player(
        self,
        *,
        public_player_id: str | None,
        ingame_name: str,
        account_name: str,
        mta_serial: str | None,
        country_code: str | None,
    ) -> Playerbase:
        row = Playerbase(
            public_player_id=public_player_id,
            ingame_name=ingame_name,
            account_name=account_name,
            mta_serial=mta_serial,
            country_code=country_code,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_player_by_id(self, player_id: int) -> Playerbase | None:
        stmt = select(Playerbase).where(Playerbase.id == player_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_player_by_account_name(self, account_name: str) -> Playerbase | None:
        stmt = select(Playerbase).where(Playerbase.account_name == account_name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_player_by_mta_serial(self, mta_serial: str) -> Playerbase | None:
        stmt = select(Playerbase).where(Playerbase.mta_serial == mta_serial)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_players(self, *, limit: int, offset: int) -> Sequence[Playerbase]:
        stmt = (
            select(Playerbase)
            .order_by(Playerbase.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_membership(
        self,
        *,
        player_id: int,
        status: str,
        joined_at,
        current_rank_id: int | None,
    ) -> GroupMembership:
        row = GroupMembership(
            player_id=player_id,
            status=status,
            joined_at=joined_at,
            current_rank_id=current_rank_id,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_membership_by_id(self, membership_id: int) -> GroupMembership | None:
        stmt = select(GroupMembership).where(GroupMembership.id == membership_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_memberships(self) -> Sequence[GroupMembership]:
        stmt = select(GroupMembership).order_by(GroupMembership.id.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_memberships_by_player(self, player_id: int) -> Sequence[GroupMembership]:
        stmt = select(GroupMembership).where(GroupMembership.player_id == player_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert_roster_entry(
        self,
        *,
        group_membership_id: int,
        display_rank: str | None,
        is_on_leave: bool,
        notes: str | None,
    ) -> GroupRoster:
        stmt = select(GroupRoster).where(GroupRoster.group_membership_id == group_membership_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            row = GroupRoster(
                group_membership_id=group_membership_id,
                display_rank=display_rank,
                is_on_leave=is_on_leave,
                notes=notes,
            )
            self.session.add(row)
            await self.session.flush()
            return row

        row.display_rank = display_rank
        row.is_on_leave = is_on_leave
        row.notes = notes
        await self.session.flush()
        return row

    async def get_roster_by_membership_id(self, membership_id: int) -> GroupRoster | None:
        stmt = select(GroupRoster).where(GroupRoster.group_membership_id == membership_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_punishment(
        self,
        *,
        player_id: int,
        punishment_type: str,
        severity: int,
        reason: str,
        issued_by_user_id: int,
        expires_at,
        status: str = "active",
    ) -> PlayerPunishment:
        row = PlayerPunishment(
            player_id=player_id,
            punishment_type=punishment_type,
            severity=severity,
            reason=reason,
            issued_by_user_id=issued_by_user_id,
            expires_at=expires_at,
            status=status,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_punishments(self, player_id: int) -> Sequence[PlayerPunishment]:
        stmt = (
            select(PlayerPunishment)
            .where(PlayerPunishment.player_id == player_id)
            .order_by(PlayerPunishment.issued_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_punishment_by_id(self, punishment_id: int) -> PlayerPunishment | None:
        stmt = select(PlayerPunishment).where(PlayerPunishment.id == punishment_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
