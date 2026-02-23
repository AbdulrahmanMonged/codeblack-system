from __future__ import annotations

from uuid import uuid4

from backend.application.dto.auth import AuthenticatedPrincipal
from backend.application.services.notification_service import NotificationService
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.order_repository import OrderRepository
from backend.infrastructure.storage.uploader import StorageUploadResult


class OrderService:
    async def submit_order(
        self,
        *,
        principal: AuthenticatedPrincipal,
        ingame_name: str,
        completed_orders: str,
        proof_upload: StorageUploadResult,
    ) -> dict:
        async with get_session() as session:
            repo = OrderRepository(session)
            account_link = await repo.get_user_game_account_by_discord(
                principal.discord_user_id
            )
            if account_link is None:
                raise ApiException(
                    status_code=422,
                    error_code="ACCOUNT_LINK_REQUIRED",
                    message="No linked account_name found for this Discord user",
                )
            if not account_link.is_verified:
                raise ApiException(
                    status_code=422,
                    error_code="VERIFIED_ACCOUNT_LINK_REQUIRED",
                    message="A verified account link is required before submitting orders",
                )

            order = await repo.create_order(
                public_id=self._generate_public_id(),
                submitted_by_user_id=principal.user_id,
                discord_user_id=principal.discord_user_id,
                ingame_name=ingame_name,
                account_name=account_link.account_name,
                completed_orders=completed_orders,
                proof_file_key=proof_upload.key,
                proof_file_url=proof_upload.url,
                proof_content_type=proof_upload.content_type,
                proof_size_bytes=proof_upload.size_bytes,
                status="submitted",
            )

            notification_service = NotificationService()
            await notification_service.dispatch_to_permissions_in_session(
                session=session,
                actor_user_id=principal.user_id,
                permission_keys={"orders.review", "orders.decision.accept", "orders.decision.deny"},
                event_type="orders.submitted",
                category="orders",
                severity="info",
                title=f"New order submitted: {order.public_id}",
                body=f"Order from {account_link.account_name} requires review.",
                entity_type="order",
                entity_public_id=order.public_id,
                metadata_json={
                    "submitted_by_user_id": order.submitted_by_user_id,
                    "account_name": order.account_name,
                    "status": order.status,
                },
                include_actor_if_missing=False,
            )
            await session.flush()
            await session.refresh(order)
            return self._order_to_dict(order)

    async def list_orders(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        async with get_session() as session:
            repo = OrderRepository(session)
            rows = await repo.list_orders(status=status, limit=limit, offset=offset)
            return [self._order_to_dict(row) for row in rows]

    async def list_orders_by_submitter(
        self,
        *,
        submitted_by_user_id: int,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        async with get_session() as session:
            repo = OrderRepository(session)
            rows = await repo.list_orders_by_submitter(
                submitted_by_user_id=submitted_by_user_id,
                status=status,
                limit=limit,
                offset=offset,
            )
            return [self._order_to_dict(row) for row in rows]

    async def get_order(
        self,
        *,
        public_id: str,
        requester_user_id: int,
        can_read_all: bool,
    ) -> dict:
        async with get_session() as session:
            repo = OrderRepository(session)
            row = await repo.get_order_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="ORDER_NOT_FOUND",
                    message=f"Order {public_id} not found",
                )
            if not can_read_all and row.submitted_by_user_id != requester_user_id:
                raise ApiException(
                    status_code=403,
                    error_code="ORDER_ACCESS_FORBIDDEN",
                    message="You can only view your own orders",
                )
            return self._order_to_dict(row)

    async def decide_order(
        self,
        *,
        public_id: str,
        reviewer_user_id: int,
        decision: str,
        reason: str | None,
    ) -> dict:
        decision_value = decision.lower().strip()
        if decision_value not in {"accepted", "denied"}:
            raise ApiException(
                status_code=422,
                error_code="INVALID_ORDER_DECISION",
                message="decision must be accepted or denied",
            )
        if decision_value == "denied" and not reason:
            raise ApiException(
                status_code=422,
                error_code="ORDER_DENIAL_REASON_REQUIRED",
                message="reason is required when decision=denied",
            )

        async with get_session() as session:
            repo = OrderRepository(session)
            row = await repo.get_order_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="ORDER_NOT_FOUND",
                    message=f"Order {public_id} not found",
                )

            row.status = decision_value
            await repo.add_order_review(
                order_id=row.id,
                reviewer_user_id=reviewer_user_id,
                decision=decision_value,
                reason=reason,
            )

            notification_service = NotificationService()
            await notification_service.dispatch_to_users_in_session(
                session=session,
                actor_user_id=reviewer_user_id,
                recipient_user_ids={row.submitted_by_user_id},
                event_type=f"orders.{decision_value}",
                category="orders",
                severity="success" if decision_value == "accepted" else "warning",
                title=f"Order {decision_value}: {row.public_id}",
                body=(
                    f"Your order {row.public_id} was {decision_value}."
                    if not reason
                    else f"Your order {row.public_id} was {decision_value}. Reviewer reason: {reason}"
                ),
                entity_type="order",
                entity_public_id=row.public_id,
                metadata_json={
                    "decision": decision_value,
                    "reviewer_user_id": reviewer_user_id,
                    "status": row.status,
                },
                include_actor_if_missing=False,
            )
            await session.flush()
            await session.refresh(row)
            return self._order_to_dict(row)

    async def link_user_account(
        self,
        *,
        user_id: int,
        discord_user_id: int,
        account_name: str,
        is_verified: bool,
    ) -> dict:
        normalized_account_name = account_name.strip().lower()
        if not normalized_account_name:
            raise ApiException(
                status_code=422,
                error_code="ACCOUNT_NAME_INVALID",
                message="account_name cannot be empty",
            )
        async with get_session() as session:
            repo = OrderRepository(session)
            row = await repo.upsert_user_game_account(
                user_id=user_id,
                discord_user_id=discord_user_id,
                account_name=normalized_account_name,
                is_verified=is_verified,
            )
            await session.flush()
            await session.refresh(row)
            return self._account_link_to_dict(row)

    async def get_user_account_link(self, *, user_id: int) -> dict:
        async with get_session() as session:
            repo = OrderRepository(session)
            row = await repo.get_user_game_account_by_user(user_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="ACCOUNT_LINK_NOT_FOUND",
                    message="No account link found for user",
                )
            return self._account_link_to_dict(row)

    @staticmethod
    def _order_to_dict(row) -> dict:
        return {
            "public_id": row.public_id,
            "status": row.status,
            "submitted_at": row.submitted_at,
            "updated_at": row.updated_at,
            "submitted_by_user_id": row.submitted_by_user_id,
            "discord_user_id": row.discord_user_id,
            "ingame_name": row.ingame_name,
            "account_name": row.account_name,
            "completed_orders": row.completed_orders,
            "proof_file_key": row.proof_file_key,
            "proof_file_url": row.proof_file_url,
            "proof_content_type": row.proof_content_type,
            "proof_size_bytes": row.proof_size_bytes,
        }

    @staticmethod
    def _account_link_to_dict(row) -> dict:
        return {
            "user_id": row.user_id,
            "discord_user_id": row.discord_user_id,
            "account_name": row.account_name,
            "is_verified": row.is_verified,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def _generate_public_id() -> str:
        return f"ORD-{uuid4().hex[:12].upper()}"
