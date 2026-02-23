from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.services.notification_service import NotificationService
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.roster_repository import RosterRepository


class RosterService:
    async def create_rank(
        self,
        *,
        name: str,
        level: int,
    ) -> dict:
        async with get_session() as session:
            repo = RosterRepository(session)
            row = await repo.create_rank(
                name=name.strip(),
                level=level,
            )
            return self._rank_to_dict(row)

    async def list_ranks(self) -> list[dict]:
        async with get_session() as session:
            repo = RosterRepository(session)
            rows = await repo.list_ranks()
            return [self._rank_to_dict(row) for row in rows]

    async def create_player(
        self,
        *,
        ingame_name: str,
        account_name: str,
        mta_serial: str | None,
        country_code: str | None,
    ) -> dict:
        normalized_account = account_name.strip().lower()
        public_player_id = f"PLY-{normalized_account[:4].upper()}-{datetime.utcnow().strftime('%H%M%S')}"
        async with get_session() as session:
            repo = RosterRepository(session)
            row = await repo.create_player(
                public_player_id=public_player_id,
                ingame_name=ingame_name.strip(),
                account_name=normalized_account,
                mta_serial=mta_serial,
                country_code=country_code,
            )
            return self._player_to_dict(row)

    async def list_players(self, *, limit: int, offset: int) -> list[dict]:
        async with get_session() as session:
            repo = RosterRepository(session)
            rows = await repo.list_players(limit=limit, offset=offset)
            return [self._player_to_dict(row) for row in rows]

    async def get_player(self, *, player_id: int) -> dict:
        async with get_session() as session:
            repo = RosterRepository(session)
            row = await repo.get_player_by_id(player_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="PLAYER_NOT_FOUND",
                    message=f"Player {player_id} not found",
                )
            return self._player_to_dict(row)

    async def create_membership(
        self,
        *,
        player_id: int,
        status: str,
        joined_at,
        current_rank_id: int | None,
        display_rank: str | None,
        is_on_leave: bool,
        notes: str | None,
    ) -> dict:
        async with get_session() as session:
            repo = RosterRepository(session)
            player = await repo.get_player_by_id(player_id)
            if player is None:
                raise ApiException(
                    status_code=404,
                    error_code="PLAYER_NOT_FOUND",
                    message=f"Player {player_id} not found",
                )

            membership = await repo.create_membership(
                player_id=player.id,
                status=status,
                joined_at=joined_at,
                current_rank_id=current_rank_id,
            )
            roster = await repo.upsert_roster_entry(
                group_membership_id=membership.id,
                display_rank=display_rank,
                is_on_leave=is_on_leave,
                notes=notes,
            )
            return self._membership_to_dict(
                membership=membership,
                player=player,
                roster=roster,
            )

    async def update_membership(
        self,
        *,
        membership_id: int,
        status: str | None,
        left_at,
        current_rank_id: int | None,
        display_rank: str | None,
        is_on_leave: bool | None,
        notes: str | None,
        actor_user_id: int | None = None,
    ) -> dict:
        async with get_session() as session:
            repo = RosterRepository(session)
            notification_service = NotificationService()
            membership = await repo.get_membership_by_id(membership_id)
            if membership is None:
                raise ApiException(
                    status_code=404,
                    error_code="MEMBERSHIP_NOT_FOUND",
                    message=f"Membership {membership_id} not found",
                )
            previous_status = membership.status
            previous_rank_id = membership.current_rank_id
            if status is not None:
                membership.status = status
            if left_at is not None:
                membership.left_at = left_at
            if current_rank_id is not None:
                membership.current_rank_id = current_rank_id

            roster = await repo.get_roster_by_membership_id(membership.id)
            if roster is None:
                roster = await repo.upsert_roster_entry(
                    group_membership_id=membership.id,
                    display_rank=display_rank,
                    is_on_leave=bool(is_on_leave),
                    notes=notes,
                )
            else:
                roster = await repo.upsert_roster_entry(
                    group_membership_id=membership.id,
                    display_rank=display_rank if display_rank is not None else roster.display_rank,
                    is_on_leave=is_on_leave if is_on_leave is not None else roster.is_on_leave,
                    notes=notes if notes is not None else roster.notes,
                )

            player = await repo.get_player_by_id(membership.player_id)
            if player is None:
                raise ApiException(
                    status_code=500,
                    error_code="MEMBERSHIP_RELATION_MISSING",
                    message="Membership relation data not found",
                )

            previous_rank = (
                await repo.get_rank_by_id(previous_rank_id)
                if previous_rank_id is not None
                else None
            )
            current_rank = (
                await repo.get_rank_by_id(membership.current_rank_id)
                if membership.current_rank_id is not None
                else None
            )
            await self._dispatch_membership_notifications(
                session=session,
                notification_service=notification_service,
                actor_user_id=actor_user_id,
                membership=membership,
                player=player,
                previous_status=previous_status,
                previous_rank=previous_rank,
                current_rank=current_rank,
                status_updated=status is not None,
                rank_updated=current_rank_id is not None,
            )

            return self._membership_to_dict(
                membership=membership,
                player=player,
                roster=roster,
            )

    async def list_roster(self, *, limit: int, offset: int) -> list[dict]:
        async with get_session() as session:
            repo = RosterRepository(session)
            memberships = await repo.list_memberships(limit=limit, offset=offset)
            result: list[dict] = []
            for membership in memberships:
                player = await repo.get_player_by_id(membership.player_id)
                roster = await repo.get_roster_by_membership_id(membership.id)
                if player is None:
                    continue
                result.append(
                    self._membership_to_dict(
                        membership=membership,
                        player=player,
                        roster=roster,
                    )
                )
            return result

    async def add_punishment(
        self,
        *,
        player_id: int,
        punishment_type: str,
        severity: int,
        reason: str,
        issued_by_user_id: int,
        expires_at,
    ) -> dict:
        async with get_session() as session:
            repo = RosterRepository(session)
            player = await repo.get_player_by_id(player_id)
            if player is None:
                raise ApiException(
                    status_code=404,
                    error_code="PLAYER_NOT_FOUND",
                    message=f"Player {player_id} not found",
                )
            row = await repo.add_punishment(
                player_id=player_id,
                punishment_type=punishment_type,
                severity=severity,
                reason=reason,
                issued_by_user_id=issued_by_user_id,
                expires_at=expires_at,
            )
            return self._punishment_to_dict(row)

    async def list_punishments(self, *, player_id: int) -> list[dict]:
        async with get_session() as session:
            repo = RosterRepository(session)
            rows = await repo.list_punishments(player_id=player_id)
            return [self._punishment_to_dict(row) for row in rows]

    async def update_punishment(
        self,
        *,
        punishment_id: int,
        status: str | None,
        expires_at,
    ) -> dict:
        async with get_session() as session:
            repo = RosterRepository(session)
            row = await repo.get_punishment_by_id(punishment_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="PUNISHMENT_NOT_FOUND",
                    message=f"Punishment {punishment_id} not found",
                )
            if status is not None:
                row.status = status
            if expires_at is not None:
                row.expires_at = expires_at
            return self._punishment_to_dict(row)

    @staticmethod
    def _rank_to_dict(row) -> dict:
        return {
            "id": row.id,
            "name": row.name,
            "level": row.level,
            "is_active": row.is_active,
        }

    @staticmethod
    def _player_to_dict(row) -> dict:
        return {
            "id": row.id,
            "public_player_id": row.public_player_id,
            "ingame_name": row.ingame_name,
            "account_name": row.account_name,
            "mta_serial": row.mta_serial,
            "country_code": row.country_code,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def _membership_to_dict(*, membership, player, roster) -> dict:
        return {
            "membership_id": membership.id,
            "player": {
                "id": player.id,
                "public_player_id": player.public_player_id,
                "ingame_name": player.ingame_name,
                "account_name": player.account_name,
            },
            "status": membership.status,
            "joined_at": membership.joined_at,
            "left_at": membership.left_at,
            "current_rank_id": membership.current_rank_id,
            "display_rank": roster.display_rank if roster else None,
            "is_on_leave": roster.is_on_leave if roster else False,
            "notes": roster.notes if roster else None,
            "updated_at": roster.updated_at if roster else membership.updated_at,
        }

    @staticmethod
    def _punishment_to_dict(row) -> dict:
        return {
            "id": row.id,
            "player_id": row.player_id,
            "punishment_type": row.punishment_type,
            "severity": row.severity,
            "reason": row.reason,
            "issued_by_user_id": row.issued_by_user_id,
            "issued_at": row.issued_at,
            "expires_at": row.expires_at,
            "status": row.status,
        }

    async def _dispatch_membership_notifications(
        self,
        *,
        session: AsyncSession,
        notification_service: NotificationService,
        actor_user_id: int | None,
        membership,
        player,
        previous_status: str,
        previous_rank,
        current_rank,
        status_updated: bool,
        rank_updated: bool,
    ) -> None:
        if status_updated and previous_status != membership.status:
            normalized_status = membership.status.strip().lower()
            if normalized_status in {"kicked", "kick"}:
                event_type = "roster.member_kicked"
                severity = "critical"
                title = f"Member kicked: {player.ingame_name}"
            else:
                event_type = "roster.member_status_changed"
                severity = "warning" if normalized_status in {"left", "inactive", "removed"} else "info"
                title = f"Roster status updated: {player.ingame_name}"

            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=actor_user_id,
                event_type=event_type,
                category="roster",
                severity=severity,
                title=title,
                body=(
                    f"{player.ingame_name} status changed from {previous_status} "
                    f"to {membership.status}."
                ),
                entity_type="membership",
                entity_public_id=str(membership.id),
                metadata_json={
                    "membership_id": membership.id,
                    "player_id": player.id,
                    "previous_status": previous_status,
                    "new_status": membership.status,
                },
            )

        if rank_updated and current_rank != previous_rank:
            previous_rank_name = previous_rank.name if previous_rank else "unassigned"
            current_rank_name = current_rank.name if current_rank else "unassigned"

            event_type = "roster.member_rank_changed"
            severity = "info"
            title = f"Rank updated: {player.ingame_name}"
            if previous_rank and current_rank:
                if current_rank.level > previous_rank.level:
                    event_type = "roster.member_promoted"
                    severity = "success"
                    title = f"Promotion: {player.ingame_name}"
                elif current_rank.level < previous_rank.level:
                    event_type = "roster.member_demoted"
                    severity = "warning"
                    title = f"Demotion: {player.ingame_name}"

            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=actor_user_id,
                event_type=event_type,
                category="roster",
                severity=severity,
                title=title,
                body=(
                    f"{player.ingame_name} rank changed from {previous_rank_name} "
                    f"to {current_rank_name}."
                ),
                entity_type="membership",
                entity_public_id=str(membership.id),
                metadata_json={
                    "membership_id": membership.id,
                    "player_id": player.id,
                    "previous_rank_id": previous_rank.id if previous_rank else None,
                    "new_rank_id": current_rank.id if current_rank else None,
                    "previous_rank_name": previous_rank_name,
                    "new_rank_name": current_rank_name,
                },
            )
