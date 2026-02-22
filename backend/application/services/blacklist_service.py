from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.application.services.notification_service import NotificationService
from backend.core.config import get_settings
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.blacklist_repository import BlacklistRepository
from backend.infrastructure.repositories.order_repository import OrderRepository


class BlacklistService:
    def __init__(self):
        self.settings = get_settings()

    async def create_entry(
        self,
        *,
        player_id: int | None,
        blacklist_level: int,
        alias: str,
        identity: str,
        serial: str | None,
        roots: str | None,
        remarks: str,
        actor_user_id: int,
    ) -> dict:
        if blacklist_level < 1:
            raise ApiException(
                status_code=422,
                error_code="BLACKLIST_LEVEL_INVALID",
                message="blacklist_level must be >= 1",
            )
        identity_value = identity.strip().lower()
        if not identity_value:
            raise ApiException(
                status_code=422,
                error_code="BLACKLIST_IDENTITY_INVALID",
                message="identity cannot be empty",
            )

        async with get_session() as session:
            repo = BlacklistRepository(session)
            existing = await repo.find_active_by_account_name(identity_value)
            if existing is not None:
                raise ApiException(
                    status_code=409,
                    error_code="BLACKLIST_ENTRY_ALREADY_ACTIVE",
                    message=f"Account {identity_value} is already blacklisted",
                )

            sequence = await repo.get_next_sequence()
            blacklist_player_id = self._format_blacklist_player_id(sequence)
            row = await repo.create_entry(
                blacklist_player_id=blacklist_player_id,
                blacklist_sequence=sequence,
                suffix_key=self.settings.BLACKLIST_SUFFIX_KEY,
                player_id=player_id,
                blacklist_level=blacklist_level,
                alias=alias.strip(),
                identity=identity_value,
                serial=serial,
                roots=roots.upper() if roots else None,
                remarks=remarks,
                status="active",
                created_by_user_id=actor_user_id,
                removed_by_user_id=None,
                removed_at=None,
            )
            await repo.add_history(
                blacklist_entry_id=row.id,
                action="created",
                actor_user_id=actor_user_id,
                change_set='{"status":"active"}',
            )
            return self._entry_to_dict(row)

    async def list_entries(self, *, status: str | None, limit: int, offset: int) -> list[dict]:
        async with get_session() as session:
            repo = BlacklistRepository(session)
            rows = await repo.list_entries(status=status, limit=limit, offset=offset)
            return [self._entry_to_dict(row) for row in rows]

    async def update_entry(
        self,
        *,
        entry_id: int,
        blacklist_level: int | None,
        alias: str | None,
        serial: str | None,
        roots: str | None,
        remarks: str | None,
        actor_user_id: int,
    ) -> dict:
        async with get_session() as session:
            repo = BlacklistRepository(session)
            row = await repo.get_entry_by_id(entry_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="BLACKLIST_ENTRY_NOT_FOUND",
                    message=f"Blacklist entry {entry_id} not found",
                )
            if blacklist_level is not None:
                row.blacklist_level = blacklist_level
            if alias is not None:
                row.alias = alias.strip()
            if serial is not None:
                row.serial = serial
            if roots is not None:
                row.roots = roots.upper()
            if remarks is not None:
                row.remarks = remarks

            await repo.add_history(
                blacklist_entry_id=row.id,
                action="updated",
                actor_user_id=actor_user_id,
                change_set='{"updated":true}',
            )
            return self._entry_to_dict(row)

    async def remove_entry(
        self,
        *,
        entry_id: int,
        actor_user_id: int,
        reason: str | None,
    ) -> dict:
        async with get_session() as session:
            repo = BlacklistRepository(session)
            row = await repo.get_entry_by_id(entry_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="BLACKLIST_ENTRY_NOT_FOUND",
                    message=f"Blacklist entry {entry_id} not found",
                )
            row.status = "removed"
            row.removed_by_user_id = actor_user_id
            row.removed_at = datetime.now(timezone.utc)
            await repo.add_history(
                blacklist_entry_id=row.id,
                action="removed",
                actor_user_id=actor_user_id,
                change_set=f'{{"reason":"{reason or ""}"}}',
            )
            return self._entry_to_dict(row)

    async def create_removal_request(
        self,
        *,
        account_name: str,
        request_text: str,
    ) -> dict:
        identity = account_name.strip().lower()
        if not identity:
            raise ApiException(
                status_code=422,
                error_code="ACCOUNT_NAME_INVALID",
                message="account_name cannot be empty",
            )
        async with get_session() as session:
            repo = BlacklistRepository(session)
            order_repo = OrderRepository(session)
            notification_service = NotificationService()

            entry = await repo.find_active_by_account_name(identity)
            if entry is None:
                raise ApiException(
                    status_code=403,
                    error_code="BLACKLIST_REMOVAL_NOT_ELIGIBLE",
                    message="Removal requests are only allowed for active blacklist entries",
                )
            pending = await repo.get_pending_removal_request_by_account(account_name=identity)
            if pending is not None:
                raise ApiException(
                    status_code=409,
                    error_code="BLACKLIST_REMOVAL_ALREADY_PENDING",
                    message="A blacklist removal request is already pending for this account",
                    details={"public_id": pending.public_id},
                )
            row = await repo.create_removal_request(
                public_id=self._removal_request_public_id(),
                blacklist_entry_id=entry.id,
                account_name=identity,
                request_text=request_text,
                status="pending",
                review_comment=None,
                reviewed_at=None,
                reviewed_by_user_id=None,
            )

            account_link = await order_repo.get_user_game_account_by_account_name(identity)
            actor_user_id = account_link.user_id if account_link else None
            await notification_service.dispatch_to_permissions_in_session(
                session=session,
                actor_user_id=actor_user_id,
                permission_keys={"blacklist_removal_requests.review"},
                event_type="blacklist_removal.submitted",
                category="blacklist",
                severity="info",
                title=f"Blacklist removal submitted: {row.public_id}",
                body=f"Blacklist removal request for {identity} is waiting for review.",
                entity_type="blacklist_removal_request",
                entity_public_id=row.public_id,
                metadata_json={
                    "account_name": identity,
                    "status": row.status,
                    "blacklist_entry_id": row.blacklist_entry_id,
                },
                include_actor_if_missing=False,
            )
            await session.flush()
            await session.refresh(row)
            return self._removal_request_to_dict(row)

    async def check_removal_eligibility(self, *, account_name: str) -> dict:
        identity = account_name.strip().lower()
        if not identity:
            raise ApiException(
                status_code=422,
                error_code="ACCOUNT_NAME_INVALID",
                message="account_name cannot be empty",
            )
        async with get_session() as session:
            repo = BlacklistRepository(session)
            entry = await repo.find_active_by_account_name(identity)
            pending = await repo.get_pending_removal_request_by_account(account_name=identity)
            recent_requests = await repo.list_removal_requests_by_account(
                account_name=identity,
                limit=5,
            )
            recent_payload = [
                {
                    "public_id": row.public_id,
                    "status": row.status,
                    "requested_at": row.requested_at,
                    "reviewed_at": row.reviewed_at,
                    "review_comment": row.review_comment,
                }
                for row in recent_requests
            ]
            if entry is None:
                return {
                    "account_name": identity,
                    "is_blacklisted": False,
                    "blacklist_entry_id": None,
                    "blacklist_player_id": None,
                    "blacklist_level": None,
                    "status": None,
                    "status_message": "Account is not currently blacklisted",
                    "can_submit": False,
                    "pending_request_public_id": pending.public_id if pending else None,
                    "recent_requests": recent_payload,
                }
            return {
                "account_name": identity,
                "is_blacklisted": True,
                "blacklist_entry_id": entry.id,
                "blacklist_player_id": entry.blacklist_player_id,
                "blacklist_level": entry.blacklist_level,
                "status": entry.status,
                "status_message": (
                    f"Active blacklist entry {entry.blacklist_player_id} found"
                    if pending is None
                    else f"Active entry found, but pending removal request {pending.public_id} already exists"
                ),
                "can_submit": pending is None,
                "pending_request_public_id": pending.public_id if pending else None,
                "recent_requests": recent_payload,
            }

    async def list_removal_requests(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        async with get_session() as session:
            repo = BlacklistRepository(session)
            rows = await repo.list_removal_requests(status=status, limit=limit, offset=offset)
            return [self._removal_request_to_dict(row) for row in rows]

    async def get_removal_request(self, *, request_id: int) -> dict:
        async with get_session() as session:
            repo = BlacklistRepository(session)
            row = await repo.get_removal_request_by_id(request_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="BLACKLIST_REMOVAL_REQUEST_NOT_FOUND",
                    message=f"Removal request {request_id} not found",
                )
            return self._removal_request_to_dict(row)

    async def review_removal_request(
        self,
        *,
        request_id: int,
        approve: bool,
        review_comment: str | None,
        reviewer_user_id: int,
    ) -> dict:
        target_status = "approved" if approve else "denied"
        async with get_session() as session:
            repo = BlacklistRepository(session)
            order_repo = OrderRepository(session)
            notification_service = NotificationService()

            row = await repo.review_removal_request(
                request_id=request_id,
                reviewer_user_id=reviewer_user_id,
                status=target_status,
                review_comment=review_comment,
            )
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="BLACKLIST_REMOVAL_REQUEST_NOT_FOUND",
                    message=f"Removal request {request_id} not found",
                )

            if approve and row.blacklist_entry_id:
                entry = await repo.get_entry_by_id(row.blacklist_entry_id)
                if entry and entry.status == "active":
                    entry.status = "removed"
                    entry.removed_at = datetime.now(timezone.utc)
                    entry.removed_by_user_id = reviewer_user_id
                    await repo.add_history(
                        blacklist_entry_id=entry.id,
                        action="removed",
                        actor_user_id=reviewer_user_id,
                        change_set='{"source":"removal_request"}',
                    )

            account_link = await order_repo.get_user_game_account_by_account_name(row.account_name)
            if account_link is not None:
                await notification_service.dispatch_to_users_in_session(
                    session=session,
                    actor_user_id=reviewer_user_id,
                    recipient_user_ids={account_link.user_id},
                    event_type=f"blacklist_removal.{target_status}",
                    category="blacklist",
                    severity="success" if approve else "warning",
                    title=f"Blacklist removal {target_status}: {row.public_id}",
                    body=(
                        f"Your blacklist removal request {row.public_id} was {target_status}."
                        if not review_comment
                        else f"Your blacklist removal request {row.public_id} was {target_status}. Reviewer comment: {review_comment}"
                    ),
                    entity_type="blacklist_removal_request",
                    entity_public_id=row.public_id,
                    metadata_json={
                        "status": row.status,
                        "account_name": row.account_name,
                        "blacklist_entry_id": row.blacklist_entry_id,
                    },
                    include_actor_if_missing=False,
                )

            await session.flush()
            await session.refresh(row)
            return self._removal_request_to_dict(row)

    def _format_blacklist_player_id(self, sequence: int) -> str:
        return f"BL{sequence:03d}{self.settings.BLACKLIST_SUFFIX_KEY}"

    @staticmethod
    def _removal_request_public_id() -> str:
        return f"BLR-{uuid4().hex[:12].upper()}"

    @staticmethod
    def _entry_to_dict(row) -> dict:
        return {
            "id": row.id,
            "blacklist_player_id": row.blacklist_player_id,
            "blacklist_sequence": row.blacklist_sequence,
            "suffix_key": row.suffix_key,
            "player_id": row.player_id,
            "blacklist_level": row.blacklist_level,
            "alias": row.alias,
            "identity": row.identity,
            "serial": row.serial,
            "roots": row.roots,
            "remarks": row.remarks,
            "status": row.status,
            "created_by_user_id": row.created_by_user_id,
            "removed_by_user_id": row.removed_by_user_id,
            "created_at": row.created_at,
            "removed_at": row.removed_at,
        }

    @staticmethod
    def _removal_request_to_dict(row) -> dict:
        return {
            "id": row.id,
            "public_id": row.public_id,
            "blacklist_entry_id": row.blacklist_entry_id,
            "account_name": row.account_name,
            "request_text": row.request_text,
            "status": row.status,
            "review_comment": row.review_comment,
            "requested_at": row.requested_at,
            "reviewed_at": row.reviewed_at,
            "reviewed_by_user_id": row.reviewed_by_user_id,
        }
