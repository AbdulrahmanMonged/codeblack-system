from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.notification_service import NotificationService
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.order_repository import OrderRepository
from backend.infrastructure.repositories.roster_repository import RosterRepository
from backend.infrastructure.repositories.verification_repository import (
    VerificationRepository,
)


class VerificationService:
    async def create_request(
        self,
        *,
        principal: AuthenticatedPrincipal,
        account_name: str,
        mta_serial: str,
        forum_url: str,
    ) -> dict:
        if principal.is_verified:
            raise ApiException(
                status_code=409,
                error_code="ALREADY_VERIFIED",
                message="Account is already verified",
            )

        normalized_account_name = self._normalize_account_name(account_name)
        normalized_serial = self._normalize_serial(mta_serial)
        normalized_forum_url = self._normalize_forum_url(forum_url)

        async with get_session() as session:
            repo = VerificationRepository(session)
            pending_requests = await repo.list_pending_for_user(user_id=principal.user_id)
            if pending_requests:
                raise ApiException(
                    status_code=409,
                    error_code="VERIFICATION_REQUEST_ALREADY_PENDING",
                    message="A verification request is already pending for this user",
                )

            row = await repo.create_request(
                public_id=self._public_id(),
                user_id=principal.user_id,
                discord_user_id=principal.discord_user_id,
                account_name=normalized_account_name,
                mta_serial=normalized_serial,
                forum_url=normalized_forum_url,
                status="pending",
                review_comment=None,
                reviewed_by_user_id=None,
                reviewed_at=None,
            )

            notification_service = NotificationService()
            await notification_service.dispatch_to_permissions_in_session(
                session=session,
                actor_user_id=principal.user_id,
                permission_keys={"verification_requests.review"},
                event_type="verification_requests.submitted",
                category="verification",
                severity="info",
                title=f"Verification submitted: {row.public_id}",
                body=f"Verification request for {row.account_name} is waiting for review.",
                entity_type="verification_request",
                entity_public_id=row.public_id,
                metadata_json={
                    "user_id": row.user_id,
                    "discord_user_id": row.discord_user_id,
                    "account_name": row.account_name,
                    "status": row.status,
                },
                include_actor_if_missing=False,
            )
            return self._to_dict(row)

    async def get_latest_for_user(self, *, user_id: int) -> dict | None:
        async with get_session() as session:
            repo = VerificationRepository(session)
            row = await repo.get_latest_for_user(user_id=user_id)
            if row is None:
                return None
            return self._to_dict(row)

    async def list_requests(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        async with get_session() as session:
            repo = VerificationRepository(session)
            rows = await repo.list_requests(status=status, limit=limit, offset=offset)
            return [self._to_dict(row) for row in rows]

    async def get_by_public_id(self, *, public_id: str) -> dict:
        async with get_session() as session:
            repo = VerificationRepository(session)
            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="VERIFICATION_REQUEST_NOT_FOUND",
                    message=f"Verification request {public_id} not found",
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
            verification_repo = VerificationRepository(session)
            order_repo = OrderRepository(session)
            roster_repo = RosterRepository(session)
            notification_service = NotificationService()

            row = await verification_repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="VERIFICATION_REQUEST_NOT_FOUND",
                    message=f"Verification request {public_id} not found",
                )
            if row.status != "pending":
                raise ApiException(
                    status_code=409,
                    error_code="VERIFICATION_REQUEST_NOT_PENDING",
                    message=f"Verification request {public_id} is already reviewed",
                )

            account_link = await order_repo.get_user_game_account_by_account_name(row.account_name)
            if account_link is not None and account_link.user_id != row.user_id:
                raise ApiException(
                    status_code=409,
                    error_code="ACCOUNT_NAME_ALREADY_LINKED",
                    message="This account_name is already linked to another user",
                )

            serial_owner = await roster_repo.get_player_by_mta_serial(row.mta_serial)
            if serial_owner is not None and serial_owner.account_name != row.account_name:
                raise ApiException(
                    status_code=409,
                    error_code="MTA_SERIAL_ALREADY_LINKED",
                    message="This MTA serial is already linked to another account",
                )

            now = datetime.now(timezone.utc)
            await order_repo.upsert_user_game_account(
                user_id=row.user_id,
                discord_user_id=row.discord_user_id,
                account_name=row.account_name,
                is_verified=True,
                mta_serial=row.mta_serial,
                forum_url=row.forum_url,
                verified_at=now,
                verified_by_user_id=reviewer_user_id,
            )

            player = await roster_repo.get_player_by_account_name(row.account_name)
            if player is None:
                await roster_repo.create_player(
                    public_player_id=self._public_player_id(row.account_name),
                    ingame_name=row.account_name,
                    account_name=row.account_name,
                    mta_serial=row.mta_serial,
                    country_code=None,
                )
            else:
                player.mta_serial = row.mta_serial

            reviewed = await verification_repo.set_review_decision(
                row=row,
                status="approved",
                review_comment=review_comment,
                reviewed_by_user_id=reviewer_user_id,
            )

            await notification_service.dispatch_to_users_in_session(
                session=session,
                actor_user_id=reviewer_user_id,
                recipient_user_ids={row.user_id},
                event_type="verification_requests.approved",
                category="verification",
                severity="success",
                title=f"Verification approved: {reviewed.public_id}",
                body=(
                    "Your verification request has been approved."
                    if not review_comment
                    else f"Your verification request has been approved. Reviewer comment: {review_comment}"
                ),
                entity_type="verification_request",
                entity_public_id=reviewed.public_id,
                metadata_json={
                    "status": reviewed.status,
                    "account_name": reviewed.account_name,
                },
                include_actor_if_missing=False,
            )
            return self._to_dict(reviewed)

    async def deny_request(
        self,
        *,
        public_id: str,
        reviewer_user_id: int,
        review_comment: str,
    ) -> dict:
        normalized_comment = review_comment.strip()
        if len(normalized_comment) < 3:
            raise ApiException(
                status_code=422,
                error_code="VERIFICATION_REVIEW_COMMENT_REQUIRED",
                message="Review comment is required for denial",
            )

        async with get_session() as session:
            repo = VerificationRepository(session)
            notification_service = NotificationService()

            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="VERIFICATION_REQUEST_NOT_FOUND",
                    message=f"Verification request {public_id} not found",
                )
            if row.status != "pending":
                raise ApiException(
                    status_code=409,
                    error_code="VERIFICATION_REQUEST_NOT_PENDING",
                    message=f"Verification request {public_id} is already reviewed",
                )

            reviewed = await repo.set_review_decision(
                row=row,
                status="denied",
                review_comment=normalized_comment,
                reviewed_by_user_id=reviewer_user_id,
            )

            await notification_service.dispatch_to_users_in_session(
                session=session,
                actor_user_id=reviewer_user_id,
                recipient_user_ids={row.user_id},
                event_type="verification_requests.denied",
                category="verification",
                severity="warning",
                title=f"Verification denied: {reviewed.public_id}",
                body=f"Your verification request was denied. Reviewer comment: {normalized_comment}",
                entity_type="verification_request",
                entity_public_id=reviewed.public_id,
                metadata_json={
                    "status": reviewed.status,
                    "account_name": reviewed.account_name,
                },
                include_actor_if_missing=False,
            )
            return self._to_dict(reviewed)

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "public_id": row.public_id,
            "user_id": row.user_id,
            "discord_user_id": row.discord_user_id,
            "account_name": row.account_name,
            "mta_serial": row.mta_serial,
            "forum_url": row.forum_url,
            "status": row.status,
            "review_comment": row.review_comment,
            "reviewed_by_user_id": row.reviewed_by_user_id,
            "reviewed_at": row.reviewed_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def _normalize_account_name(value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) < 2:
            raise ApiException(
                status_code=422,
                error_code="ACCOUNT_NAME_INVALID",
                message="account_name must contain at least 2 characters",
            )
        return normalized

    @staticmethod
    def _normalize_serial(value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) < 10:
            raise ApiException(
                status_code=422,
                error_code="MTA_SERIAL_INVALID",
                message="mta_serial appears invalid",
            )
        return normalized

    @staticmethod
    def _normalize_forum_url(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ApiException(
                status_code=422,
                error_code="FORUM_URL_INVALID",
                message="forum_url cannot be empty",
            )
        return normalized

    @staticmethod
    def _public_id() -> str:
        return f"VRF-{uuid4().hex[:12].upper()}"

    @staticmethod
    def _public_player_id(account_name: str) -> str:
        account_key = account_name[:4].upper().ljust(4, "X")
        return f"PLY-{account_key}-{uuid4().hex[:6].upper()}"
