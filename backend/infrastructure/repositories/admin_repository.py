from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.activities import GroupActivity
from backend.infrastructure.db.models.audit import AuditEvent
from backend.infrastructure.db.models.blacklist import (
    BlacklistEntry,
    BlacklistHistory,
    BlacklistRemovalRequest,
)
from backend.infrastructure.db.models.config_registry import ConfigChangeHistory
from backend.infrastructure.db.models.orders import Order, OrderReview
from backend.infrastructure.db.models.portal import VerificationRequest
from backend.infrastructure.db.models.recruitment import Application, ApplicationDecision
from backend.infrastructure.db.models.vacations import VacationRequest


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dashboard_summary_counts(self) -> dict[str, int]:
        applications_total = await self._count_rows(Application)
        applications_pending = await self._count_rows(
            Application, Application.status.in_(("submitted", "under_review"))
        )

        orders_total = await self._count_rows(Order)
        orders_pending = await self._count_rows(Order, Order.status == "submitted")

        activities_total = await self._count_rows(GroupActivity)
        activities_pending = await self._count_rows(
            GroupActivity, GroupActivity.status == "pending"
        )

        vacations_total = await self._count_rows(VacationRequest)
        vacations_pending = await self._count_rows(
            VacationRequest, VacationRequest.status == "pending"
        )

        removal_total = await self._count_rows(BlacklistRemovalRequest)
        removal_pending = await self._count_rows(
            BlacklistRemovalRequest,
            BlacklistRemovalRequest.status == "pending",
        )

        config_pending = await self._count_rows(
            ConfigChangeHistory,
            ConfigChangeHistory.status == "pending_approval",
        )
        verification_total = await self._count_rows(VerificationRequest)
        verification_pending = await self._count_rows(
            VerificationRequest,
            VerificationRequest.status == "pending",
        )

        return {
            "applications_total": applications_total,
            "applications_pending": applications_pending,
            "orders_total": orders_total,
            "orders_pending": orders_pending,
            "activities_total": activities_total,
            "activities_pending": activities_pending,
            "vacations_total": vacations_total,
            "vacations_pending": vacations_pending,
            "blacklist_removal_requests_total": removal_total,
            "blacklist_removal_requests_pending": removal_pending,
            "verification_requests_total": verification_total,
            "verification_requests_pending": verification_pending,
            "config_changes_pending_approval": config_pending,
        }

    async def list_review_queue_items(
        self,
        *,
        item_types: set[str],
        status: str | None,
        search: str | None,
        pending_only: bool,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        search_pattern = self._search_pattern(search)
        cap = max(fetch_size, 1)

        if "applications" in item_types:
            items.extend(
                await self._list_application_queue_items(
                    status=status,
                    search_pattern=search_pattern,
                    pending_only=pending_only,
                    fetch_size=cap,
                )
            )
        if "orders" in item_types:
            items.extend(
                await self._list_order_queue_items(
                    status=status,
                    search_pattern=search_pattern,
                    pending_only=pending_only,
                    fetch_size=cap,
                )
            )
        if "activities" in item_types:
            items.extend(
                await self._list_activity_queue_items(
                    status=status,
                    search_pattern=search_pattern,
                    pending_only=pending_only,
                    fetch_size=cap,
                )
            )
        if "vacations" in item_types:
            items.extend(
                await self._list_vacation_queue_items(
                    status=status,
                    search_pattern=search_pattern,
                    pending_only=pending_only,
                    fetch_size=cap,
                )
            )
        if "blacklist_removals" in item_types:
            items.extend(
                await self._list_blacklist_removal_queue_items(
                    status=status,
                    search_pattern=search_pattern,
                    pending_only=pending_only,
                    fetch_size=cap,
                )
            )
        if "config_changes" in item_types:
            items.extend(
                await self._list_config_change_queue_items(
                    status=status,
                    search_pattern=search_pattern,
                    pending_only=pending_only,
                    fetch_size=cap,
                )
            )
        if "verification_requests" in item_types:
            items.extend(
                await self._list_verification_queue_items(
                    status=status,
                    search_pattern=search_pattern,
                    pending_only=pending_only,
                    fetch_size=cap,
                )
            )

        items.sort(key=lambda item: item["queued_at"], reverse=True)
        return items

    async def list_audit_timeline_events(
        self,
        *,
        event_types: set[str],
        actor_user_id: int | None,
        search: str | None,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        search_pattern = self._search_pattern(search)
        cap = max(fetch_size, 1)

        if "applications" in event_types:
            events.extend(
                await self._list_application_decision_events(
                    actor_user_id=actor_user_id,
                    search_pattern=search_pattern,
                    fetch_size=cap,
                )
            )
        if "orders" in event_types:
            events.extend(
                await self._list_order_review_events(
                    actor_user_id=actor_user_id,
                    search_pattern=search_pattern,
                    fetch_size=cap,
                )
            )
        if "activities" in event_types:
            events.extend(
                await self._list_activity_review_events(
                    actor_user_id=actor_user_id,
                    search_pattern=search_pattern,
                    fetch_size=cap,
                )
            )
        if "vacations" in event_types:
            events.extend(
                await self._list_vacation_review_events(
                    actor_user_id=actor_user_id,
                    search_pattern=search_pattern,
                    fetch_size=cap,
                )
            )
        if "blacklist" in event_types:
            events.extend(
                await self._list_blacklist_history_events(
                    actor_user_id=actor_user_id,
                    search_pattern=search_pattern,
                    fetch_size=cap,
                )
            )
        if "config" in event_types:
            events.extend(
                await self._list_config_change_events(
                    actor_user_id=actor_user_id,
                    search_pattern=search_pattern,
                    fetch_size=cap,
                )
            )
        if "audit" in event_types:
            events.extend(
                await self._list_generic_audit_events(
                    actor_user_id=actor_user_id,
                    search_pattern=search_pattern,
                    fetch_size=cap,
                )
            )

        events.sort(key=lambda event: event["occurred_at"], reverse=True)
        return events

    async def _count_rows(self, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for condition in conditions:
            stmt = stmt.where(condition)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def _list_application_queue_items(
        self,
        *,
        status: str | None,
        search_pattern: str | None,
        pending_only: bool,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = select(
            Application.public_id,
            Application.status,
            Application.submitted_at,
            Application.in_game_nickname,
            Application.account_name,
            Application.mta_serial,
            Application.submitter_type,
        ).order_by(Application.submitted_at.desc())
        if status:
            stmt = stmt.where(Application.status == status)
        elif pending_only:
            stmt = stmt.where(Application.status.in_(("submitted", "under_review")))
        if search_pattern:
            stmt = stmt.where(
                or_(
                    Application.public_id.ilike(search_pattern),
                    Application.account_name.ilike(search_pattern),
                    Application.in_game_nickname.ilike(search_pattern),
                    Application.mta_serial.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "item_type": "applications",
                "item_id": row.public_id,
                "status": row.status,
                "queued_at": row.submitted_at,
                "title": f"{row.in_game_nickname} ({row.account_name})",
                "subtitle": f"Submitter: {row.submitter_type}",
                "metadata": {"mta_serial": row.mta_serial},
            }
            for row in rows
        ]

    async def _list_order_queue_items(
        self,
        *,
        status: str | None,
        search_pattern: str | None,
        pending_only: bool,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = select(
            Order.public_id,
            Order.status,
            Order.submitted_at,
            Order.ingame_name,
            Order.account_name,
            Order.discord_user_id,
        ).order_by(Order.submitted_at.desc())
        if status:
            stmt = stmt.where(Order.status == status)
        elif pending_only:
            stmt = stmt.where(Order.status == "submitted")
        if search_pattern:
            stmt = stmt.where(
                or_(
                    Order.public_id.ilike(search_pattern),
                    Order.ingame_name.ilike(search_pattern),
                    Order.account_name.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "item_type": "orders",
                "item_id": row.public_id,
                "status": row.status,
                "queued_at": row.submitted_at,
                "title": f"{row.ingame_name} ({row.account_name})",
                "subtitle": f"Discord user: {row.discord_user_id}",
                "metadata": None,
            }
            for row in rows
        ]

    async def _list_activity_queue_items(
        self,
        *,
        status: str | None,
        search_pattern: str | None,
        pending_only: bool,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = select(
            GroupActivity.public_id,
            GroupActivity.status,
            GroupActivity.created_at,
            GroupActivity.activity_type,
            GroupActivity.title,
            GroupActivity.created_by_user_id,
            GroupActivity.scheduled_for,
        ).order_by(GroupActivity.created_at.desc())
        if status:
            stmt = stmt.where(GroupActivity.status == status)
        elif pending_only:
            stmt = stmt.where(GroupActivity.status == "pending")
        if search_pattern:
            stmt = stmt.where(
                or_(
                    GroupActivity.public_id.ilike(search_pattern),
                    GroupActivity.title.ilike(search_pattern),
                    GroupActivity.activity_type.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "item_type": "activities",
                "item_id": row.public_id,
                "status": row.status,
                "queued_at": row.created_at,
                "title": f"[{row.activity_type}] {row.title}",
                "subtitle": f"Created by user {row.created_by_user_id}",
                "metadata": {
                    "scheduled_for": row.scheduled_for,
                },
            }
            for row in rows
        ]

    async def _list_vacation_queue_items(
        self,
        *,
        status: str | None,
        search_pattern: str | None,
        pending_only: bool,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = select(
            VacationRequest.public_id,
            VacationRequest.status,
            VacationRequest.created_at,
            VacationRequest.player_id,
            VacationRequest.leave_date,
            VacationRequest.expected_return_date,
            VacationRequest.target_group,
        ).order_by(VacationRequest.created_at.desc())
        if status:
            stmt = stmt.where(VacationRequest.status == status)
        elif pending_only:
            stmt = stmt.where(VacationRequest.status == "pending")
        if search_pattern:
            stmt = stmt.where(
                or_(
                    VacationRequest.public_id.ilike(search_pattern),
                    VacationRequest.target_group.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "item_type": "vacations",
                "item_id": row.public_id,
                "status": row.status,
                "queued_at": row.created_at,
                "title": f"Player #{row.player_id} vacation request",
                "subtitle": f"{row.leave_date} -> {row.expected_return_date}",
                "metadata": {"target_group": row.target_group},
            }
            for row in rows
        ]

    async def _list_blacklist_removal_queue_items(
        self,
        *,
        status: str | None,
        search_pattern: str | None,
        pending_only: bool,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = select(
            BlacklistRemovalRequest.public_id,
            BlacklistRemovalRequest.status,
            BlacklistRemovalRequest.requested_at,
            BlacklistRemovalRequest.account_name,
        ).order_by(BlacklistRemovalRequest.requested_at.desc())
        if status:
            stmt = stmt.where(BlacklistRemovalRequest.status == status)
        elif pending_only:
            stmt = stmt.where(BlacklistRemovalRequest.status == "pending")
        if search_pattern:
            stmt = stmt.where(
                or_(
                    BlacklistRemovalRequest.public_id.ilike(search_pattern),
                    BlacklistRemovalRequest.account_name.ilike(search_pattern),
                    BlacklistRemovalRequest.request_text.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "item_type": "blacklist_removals",
                "item_id": row.public_id,
                "status": row.status,
                "queued_at": row.requested_at,
                "title": f"Blacklist removal: {row.account_name}",
                "subtitle": None,
                "metadata": None,
            }
            for row in rows
        ]

    async def _list_config_change_queue_items(
        self,
        *,
        status: str | None,
        search_pattern: str | None,
        pending_only: bool,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = select(
            ConfigChangeHistory.id,
            ConfigChangeHistory.config_key,
            ConfigChangeHistory.status,
            ConfigChangeHistory.created_at,
            ConfigChangeHistory.changed_by_user_id,
            ConfigChangeHistory.change_reason,
        ).order_by(ConfigChangeHistory.created_at.desc())
        if status:
            stmt = stmt.where(ConfigChangeHistory.status == status)
        elif pending_only:
            stmt = stmt.where(ConfigChangeHistory.status == "pending_approval")
        if search_pattern:
            stmt = stmt.where(
                or_(
                    ConfigChangeHistory.config_key.ilike(search_pattern),
                    ConfigChangeHistory.change_reason.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "item_type": "config_changes",
                "item_id": str(row.id),
                "status": row.status,
                "queued_at": row.created_at,
                "title": f"Config key: {row.config_key}",
                "subtitle": f"Changed by user {row.changed_by_user_id}",
                "metadata": {"change_reason": row.change_reason},
            }
            for row in rows
        ]

    async def _list_verification_queue_items(
        self,
        *,
        status: str | None,
        search_pattern: str | None,
        pending_only: bool,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = select(
            VerificationRequest.public_id,
            VerificationRequest.status,
            VerificationRequest.created_at,
            VerificationRequest.account_name,
            VerificationRequest.mta_serial,
            VerificationRequest.user_id,
        ).order_by(VerificationRequest.created_at.desc())
        if status:
            stmt = stmt.where(VerificationRequest.status == status)
        elif pending_only:
            stmt = stmt.where(VerificationRequest.status == "pending")
        if search_pattern:
            stmt = stmt.where(
                or_(
                    VerificationRequest.public_id.ilike(search_pattern),
                    VerificationRequest.account_name.ilike(search_pattern),
                    VerificationRequest.mta_serial.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "item_type": "verification_requests",
                "item_id": row.public_id,
                "status": row.status,
                "queued_at": row.created_at,
                "title": f"{row.account_name} verification request",
                "subtitle": f"User #{row.user_id}",
                "metadata": {"mta_serial": row.mta_serial},
            }
            for row in rows
        ]

    async def _list_application_decision_events(
        self,
        *,
        actor_user_id: int | None,
        search_pattern: str | None,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                Application.public_id,
                Application.account_name,
                ApplicationDecision.decision,
                ApplicationDecision.decision_reason,
                ApplicationDecision.reviewer_user_id,
                ApplicationDecision.created_at,
            )
            .join(Application, Application.id == ApplicationDecision.application_id)
            .order_by(ApplicationDecision.created_at.desc())
        )
        if actor_user_id is not None:
            stmt = stmt.where(ApplicationDecision.reviewer_user_id == actor_user_id)
        if search_pattern:
            stmt = stmt.where(
                or_(
                    Application.public_id.ilike(search_pattern),
                    Application.account_name.ilike(search_pattern),
                    ApplicationDecision.decision_reason.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "event_type": "application.decision",
                "entity_type": "application",
                "entity_id": row.public_id,
                "action": row.decision,
                "actor_user_id": row.reviewer_user_id,
                "occurred_at": row.created_at,
                "summary": f"Application {row.public_id} marked {row.decision}",
                "metadata": {
                    "account_name": row.account_name,
                    "decision_reason": row.decision_reason,
                },
            }
            for row in rows
        ]

    async def _list_order_review_events(
        self,
        *,
        actor_user_id: int | None,
        search_pattern: str | None,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                Order.public_id,
                Order.account_name,
                OrderReview.decision,
                OrderReview.reason,
                OrderReview.reviewer_user_id,
                OrderReview.reviewed_at,
            )
            .join(Order, Order.id == OrderReview.order_id)
            .order_by(OrderReview.reviewed_at.desc())
        )
        if actor_user_id is not None:
            stmt = stmt.where(OrderReview.reviewer_user_id == actor_user_id)
        if search_pattern:
            stmt = stmt.where(
                or_(
                    Order.public_id.ilike(search_pattern),
                    Order.account_name.ilike(search_pattern),
                    OrderReview.reason.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "event_type": "order.review",
                "entity_type": "order",
                "entity_id": row.public_id,
                "action": row.decision,
                "actor_user_id": row.reviewer_user_id,
                "occurred_at": row.reviewed_at,
                "summary": f"Order {row.public_id} marked {row.decision}",
                "metadata": {
                    "account_name": row.account_name,
                    "reason": row.reason,
                },
            }
            for row in rows
        ]

    async def _list_activity_review_events(
        self,
        *,
        actor_user_id: int | None,
        search_pattern: str | None,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        moderated_statuses = ("approved", "rejected", "scheduled", "posted", "completed")
        stmt = (
            select(
                GroupActivity.public_id,
                GroupActivity.title,
                GroupActivity.status,
                GroupActivity.approved_by_user_id,
                GroupActivity.approval_comment,
                GroupActivity.updated_at,
            )
            .where(
                GroupActivity.approved_by_user_id.is_not(None),
                GroupActivity.status.in_(moderated_statuses),
            )
            .order_by(GroupActivity.updated_at.desc())
        )
        if actor_user_id is not None:
            stmt = stmt.where(GroupActivity.approved_by_user_id == actor_user_id)
        if search_pattern:
            stmt = stmt.where(
                or_(
                    GroupActivity.public_id.ilike(search_pattern),
                    GroupActivity.title.ilike(search_pattern),
                    GroupActivity.approval_comment.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "event_type": "activity.review",
                "entity_type": "activity",
                "entity_id": row.public_id,
                "action": row.status,
                "actor_user_id": row.approved_by_user_id,
                "occurred_at": row.updated_at,
                "summary": f"Activity {row.public_id} moved to {row.status}",
                "metadata": {
                    "title": row.title,
                    "comment": row.approval_comment,
                },
            }
            for row in rows
        ]

    async def _list_vacation_review_events(
        self,
        *,
        actor_user_id: int | None,
        search_pattern: str | None,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                VacationRequest.public_id,
                VacationRequest.player_id,
                VacationRequest.status,
                VacationRequest.review_comment,
                VacationRequest.reviewed_by_user_id,
                VacationRequest.reviewed_at,
            )
            .where(
                VacationRequest.reviewed_by_user_id.is_not(None),
                VacationRequest.reviewed_at.is_not(None),
            )
            .order_by(VacationRequest.reviewed_at.desc())
        )
        if actor_user_id is not None:
            stmt = stmt.where(VacationRequest.reviewed_by_user_id == actor_user_id)
        if search_pattern:
            stmt = stmt.where(
                or_(
                    VacationRequest.public_id.ilike(search_pattern),
                    VacationRequest.target_group.ilike(search_pattern),
                    VacationRequest.review_comment.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "event_type": "vacation.review",
                "entity_type": "vacation",
                "entity_id": row.public_id,
                "action": row.status,
                "actor_user_id": row.reviewed_by_user_id,
                "occurred_at": row.reviewed_at,
                "summary": f"Vacation {row.public_id} marked {row.status}",
                "metadata": {
                    "player_id": row.player_id,
                    "comment": row.review_comment,
                },
            }
            for row in rows
        ]

    async def _list_blacklist_history_events(
        self,
        *,
        actor_user_id: int | None,
        search_pattern: str | None,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                BlacklistHistory.action,
                BlacklistHistory.actor_user_id,
                BlacklistHistory.change_set,
                BlacklistHistory.created_at,
                BlacklistEntry.blacklist_player_id,
                BlacklistEntry.identity,
            )
            .join(BlacklistEntry, BlacklistEntry.id == BlacklistHistory.blacklist_entry_id)
            .order_by(BlacklistHistory.created_at.desc())
        )
        if actor_user_id is not None:
            stmt = stmt.where(BlacklistHistory.actor_user_id == actor_user_id)
        if search_pattern:
            stmt = stmt.where(
                or_(
                    BlacklistEntry.blacklist_player_id.ilike(search_pattern),
                    BlacklistEntry.identity.ilike(search_pattern),
                    BlacklistHistory.change_set.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "event_type": "blacklist.history",
                "entity_type": "blacklist",
                "entity_id": row.blacklist_player_id,
                "action": row.action,
                "actor_user_id": row.actor_user_id,
                "occurred_at": row.created_at,
                "summary": f"Blacklist {row.blacklist_player_id} action={row.action}",
                "metadata": {
                    "identity": row.identity,
                    "change_set": row.change_set,
                },
            }
            for row in rows
        ]

    async def _list_config_change_events(
        self,
        *,
        actor_user_id: int | None,
        search_pattern: str | None,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = select(
            ConfigChangeHistory.id,
            ConfigChangeHistory.config_key,
            ConfigChangeHistory.status,
            ConfigChangeHistory.change_reason,
            ConfigChangeHistory.changed_by_user_id,
            ConfigChangeHistory.approved_by_user_id,
            ConfigChangeHistory.created_at,
            ConfigChangeHistory.approved_at,
            ConfigChangeHistory.requires_approval,
        ).order_by(ConfigChangeHistory.created_at.desc())
        if actor_user_id is not None:
            stmt = stmt.where(
                or_(
                    ConfigChangeHistory.changed_by_user_id == actor_user_id,
                    ConfigChangeHistory.approved_by_user_id == actor_user_id,
                )
            )
        if search_pattern:
            stmt = stmt.where(
                or_(
                    ConfigChangeHistory.config_key.ilike(search_pattern),
                    ConfigChangeHistory.change_reason.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()

        events: list[dict[str, Any]] = []
        for row in rows:
            events.append(
                {
                    "event_type": "config.change",
                    "entity_type": "config_registry",
                    "entity_id": row.config_key,
                    "action": row.status,
                    "actor_user_id": row.changed_by_user_id,
                    "occurred_at": row.created_at,
                    "summary": f"Config {row.config_key} changed ({row.status})",
                    "metadata": {
                        "change_id": row.id,
                        "requires_approval": row.requires_approval,
                        "change_reason": row.change_reason,
                    },
                }
            )
            if row.approved_by_user_id is not None and row.approved_at is not None:
                events.append(
                    {
                        "event_type": "config.approval",
                        "entity_type": "config_registry",
                        "entity_id": row.config_key,
                        "action": "approved",
                        "actor_user_id": row.approved_by_user_id,
                        "occurred_at": row.approved_at,
                        "summary": f"Config {row.config_key} approved",
                        "metadata": {"change_id": row.id},
                    }
                )
        return events

    async def _list_generic_audit_events(
        self,
        *,
        actor_user_id: int | None,
        search_pattern: str | None,
        fetch_size: int,
    ) -> list[dict[str, Any]]:
        stmt = select(
            AuditEvent.event_type,
            AuditEvent.entity_type,
            AuditEvent.entity_id,
            AuditEvent.action,
            AuditEvent.actor_user_id,
            AuditEvent.created_at,
            AuditEvent.details_json,
        ).order_by(AuditEvent.created_at.desc())
        if actor_user_id is not None:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if search_pattern:
            stmt = stmt.where(
                or_(
                    AuditEvent.event_type.ilike(search_pattern),
                    AuditEvent.entity_type.ilike(search_pattern),
                    AuditEvent.entity_id.ilike(search_pattern),
                    AuditEvent.action.ilike(search_pattern),
                )
            )
        stmt = stmt.limit(fetch_size)
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "event_type": row.event_type,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id or "-",
                "action": row.action,
                "actor_user_id": row.actor_user_id,
                "occurred_at": row.created_at,
                "summary": f"Audit event {row.event_type}",
                "metadata": row.details_json or {},
            }
            for row in rows
        ]

    @staticmethod
    def _search_pattern(search: str | None) -> str | None:
        if search is None:
            return None
        normalized = search.strip()
        if not normalized:
            return None
        return f"%{normalized}%"
