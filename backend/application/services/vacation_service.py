from __future__ import annotations

from datetime import date
from uuid import uuid4

from backend.application.services.notification_service import NotificationService
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.config_registry_repository import (
    ConfigRegistryRepository,
)
from backend.infrastructure.repositories.order_repository import OrderRepository
from backend.infrastructure.repositories.roster_repository import RosterRepository
from backend.infrastructure.repositories.vacation_repository import VacationRepository


class VacationService:
    MAX_DURATION_CONFIG_KEY = "vacations.max_duration_days"
    DEFAULT_MAX_DURATION_DAYS = 7

    async def submit_request(
        self,
        *,
        requester_user_id: int,
        leave_date: date,
        expected_return_date: date,
        target_group: str | None,
        reason: str | None,
    ) -> dict:
        if expected_return_date < leave_date:
            raise ApiException(
                status_code=422,
                error_code="VACATION_DATE_INVALID",
                message="expected_return_date must be on or after leave_date",
            )

        policies = await self.get_policies()
        duration_days = (expected_return_date - leave_date).days + 1
        if duration_days > policies["max_duration_days"]:
            raise ApiException(
                status_code=422,
                error_code="VACATION_MAX_DURATION_EXCEEDED",
                message=f"Vacation duration exceeds configured max of {policies['max_duration_days']} days",
            )

        async with get_session() as session:
            roster_repo = RosterRepository(session)
            order_repo = OrderRepository(session)
            account_link = await order_repo.get_user_game_account_by_user(requester_user_id)
            if account_link is None or not account_link.is_verified:
                raise ApiException(
                    status_code=422,
                    error_code="VERIFIED_ACCOUNT_LINK_REQUIRED",
                    message="A verified account link is required before submitting vacation requests",
                )
            player = await roster_repo.get_player_by_account_name(account_link.account_name)
            if player is None:
                player = await roster_repo.create_player(
                    public_player_id=None,
                    ingame_name=account_link.account_name,
                    account_name=account_link.account_name,
                    mta_serial=account_link.mta_serial,
                    country_code=None,
                )
            repo = VacationRepository(session)
            row = await repo.create_request(
                public_id=self._public_id(),
                player_id=player.id,
                requester_user_id=requester_user_id,
                leave_date=leave_date,
                expected_return_date=expected_return_date,
                target_group=target_group,
                status="pending",
                reason=reason,
                review_comment=None,
                reviewed_by_user_id=None,
                reviewed_at=None,
            )

            notification_service = NotificationService()
            await notification_service.dispatch_to_permissions_in_session(
                session=session,
                actor_user_id=requester_user_id,
                permission_keys={"vacations.approve", "vacations.deny"},
                event_type="vacations.submitted",
                category="vacations",
                severity="info",
                title=f"Vacation submitted: {row.public_id}",
                body=(
                    f"Vacation request from {account_link.account_name} is waiting for review."
                ),
                entity_type="vacation",
                entity_public_id=row.public_id,
                metadata_json={
                    "player_id": row.player_id,
                    "requester_user_id": requester_user_id,
                    "leave_date": row.leave_date.isoformat(),
                    "expected_return_date": row.expected_return_date.isoformat(),
                    "status": row.status,
                },
                include_actor_if_missing=False,
            )
            await session.flush()
            await session.refresh(row)
            return self._to_dict(row)

    async def list_requests(
        self,
        *,
        status: str | None,
        player_id: int | None,
        requester_user_id: int | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        async with get_session() as session:
            repo = VacationRepository(session)
            rows = await repo.list_requests(
                status=status,
                player_id=player_id,
                requester_user_id=requester_user_id,
                limit=limit,
                offset=offset,
            )
            return [self._to_dict(row) for row in rows]

    async def get_request(self, *, public_id: str) -> dict:
        async with get_session() as session:
            repo = VacationRepository(session)
            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="VACATION_REQUEST_NOT_FOUND",
                    message=f"Vacation request {public_id} not found",
                )
            return self._to_dict(row)

    async def approve_request(
        self,
        *,
        public_id: str,
        reviewer_user_id: int,
        review_comment: str | None,
    ) -> dict:
        async with get_session() as session:
            repo = VacationRepository(session)
            roster_repo = RosterRepository(session)
            notification_service = NotificationService()
            row = await repo.review_request(
                public_id=public_id,
                reviewer_user_id=reviewer_user_id,
                status="approved",
                review_comment=review_comment,
            )
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="VACATION_REQUEST_NOT_FOUND",
                    message=f"Vacation request {public_id} not found",
                )

            memberships = await roster_repo.list_memberships_by_player(row.player_id)
            for membership in memberships:
                roster_entry = await roster_repo.get_roster_by_membership_id(membership.id)
                if roster_entry is None:
                    await roster_repo.upsert_roster_entry(
                        group_membership_id=membership.id,
                        display_rank=None,
                        is_on_leave=True,
                        notes="Set on leave from vacation approval",
                    )
                else:
                    await roster_repo.upsert_roster_entry(
                        group_membership_id=membership.id,
                        display_rank=roster_entry.display_rank,
                        is_on_leave=True,
                        notes=roster_entry.notes,
                    )

            await notification_service.dispatch_to_users_in_session(
                session=session,
                actor_user_id=reviewer_user_id,
                recipient_user_ids={row.requester_user_id},
                event_type="vacations.approved",
                category="vacations",
                severity="success",
                title=f"Vacation approved: {row.public_id}",
                body=(
                    "Your vacation request was approved."
                    if not review_comment
                    else f"Your vacation request was approved. Reviewer comment: {review_comment}"
                ),
                entity_type="vacation",
                entity_public_id=row.public_id,
                metadata_json={
                    "player_id": row.player_id,
                    "leave_date": row.leave_date.isoformat(),
                    "expected_return_date": row.expected_return_date.isoformat(),
                    "status": row.status,
                },
                include_actor_if_missing=False,
            )
            await session.flush()
            await session.refresh(row)
            return self._to_dict(row)

    async def deny_request(
        self,
        *,
        public_id: str,
        reviewer_user_id: int,
        review_comment: str | None,
    ) -> dict:
        async with get_session() as session:
            repo = VacationRepository(session)
            notification_service = NotificationService()
            row = await repo.review_request(
                public_id=public_id,
                reviewer_user_id=reviewer_user_id,
                status="denied",
                review_comment=review_comment,
            )
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="VACATION_REQUEST_NOT_FOUND",
                    message=f"Vacation request {public_id} not found",
                )

            await notification_service.dispatch_to_users_in_session(
                session=session,
                actor_user_id=reviewer_user_id,
                recipient_user_ids={row.requester_user_id},
                event_type="vacations.denied",
                category="vacations",
                severity="warning",
                title=f"Vacation denied: {row.public_id}",
                body=(
                    "Your vacation request was denied."
                    if not review_comment
                    else f"Your vacation request was denied. Reviewer comment: {review_comment}"
                ),
                entity_type="vacation",
                entity_public_id=row.public_id,
                metadata_json={
                    "player_id": row.player_id,
                    "leave_date": row.leave_date.isoformat(),
                    "expected_return_date": row.expected_return_date.isoformat(),
                    "status": row.status,
                },
                include_actor_if_missing=False,
            )
            await session.flush()
            await session.refresh(row)
            return self._to_dict(row)

    async def cancel_request(
        self,
        *,
        public_id: str,
        requester_user_id: int,
    ) -> dict:
        async with get_session() as session:
            repo = VacationRepository(session)
            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="VACATION_REQUEST_NOT_FOUND",
                    message=f"Vacation request {public_id} not found",
                )
            if row.requester_user_id != requester_user_id:
                raise ApiException(
                    status_code=403,
                    error_code="VACATION_CANCEL_FORBIDDEN",
                    message="Only request owner can cancel this vacation request",
                )
            row.status = "cancelled"
            await session.flush()
            await session.refresh(row)
            return self._to_dict(row)

    async def mark_returned(
        self,
        *,
        public_id: str,
        reviewer_user_id: int,
        review_comment: str | None,
    ) -> dict:
        async with get_session() as session:
            repo = VacationRepository(session)
            roster_repo = RosterRepository(session)
            notification_service = NotificationService()
            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="VACATION_REQUEST_NOT_FOUND",
                    message=f"Vacation request {public_id} not found",
                )
            row.status = "returned"
            row.reviewed_by_user_id = reviewer_user_id
            row.review_comment = review_comment

            memberships = await roster_repo.list_memberships_by_player(row.player_id)
            for membership in memberships:
                roster_entry = await roster_repo.get_roster_by_membership_id(membership.id)
                if roster_entry is None:
                    continue
                await roster_repo.upsert_roster_entry(
                    group_membership_id=membership.id,
                    display_rank=roster_entry.display_rank,
                    is_on_leave=False,
                    notes=roster_entry.notes,
                )

            await notification_service.dispatch_to_users_in_session(
                session=session,
                actor_user_id=reviewer_user_id,
                recipient_user_ids={row.requester_user_id},
                event_type="vacations.returned",
                category="vacations",
                severity="info",
                title=f"Vacation closed: {row.public_id}",
                body=(
                    "Your vacation request was marked as returned."
                    if not review_comment
                    else f"Your vacation request was marked as returned. Reviewer comment: {review_comment}"
                ),
                entity_type="vacation",
                entity_public_id=row.public_id,
                metadata_json={
                    "player_id": row.player_id,
                    "leave_date": row.leave_date.isoformat(),
                    "expected_return_date": row.expected_return_date.isoformat(),
                    "status": row.status,
                },
                include_actor_if_missing=False,
            )
            await session.flush()
            await session.refresh(row)
            return self._to_dict(row)

    async def get_policies(self) -> dict[str, int]:
        async with get_session() as session:
            config_repo = ConfigRegistryRepository(session)
            row = await config_repo.get_by_key(self.MAX_DURATION_CONFIG_KEY)
            if row and isinstance(row.value_json, int):
                max_duration_days = max(1, min(30, row.value_json))
            else:
                max_duration_days = self.DEFAULT_MAX_DURATION_DAYS
            return {"max_duration_days": max_duration_days}

    @staticmethod
    def _public_id() -> str:
        return f"VAC-{uuid4().hex[:12].upper()}"

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "public_id": row.public_id,
            "player_id": row.player_id,
            "requester_user_id": row.requester_user_id,
            "leave_date": row.leave_date,
            "expected_return_date": row.expected_return_date,
            "target_group": row.target_group,
            "status": row.status,
            "reason": row.reason,
            "review_comment": row.review_comment,
            "reviewed_by_user_id": row.reviewed_by_user_id,
            "reviewed_at": row.reviewed_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
