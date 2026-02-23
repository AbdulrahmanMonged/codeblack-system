from __future__ import annotations

from datetime import datetime, timezone

from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.admin_repository import AdminRepository


class AdminService:
    REVIEW_ITEM_TYPES = frozenset(
        {
            "applications",
            "orders",
            "activities",
            "vacations",
            "blacklist_removals",
            "config_changes",
            "verification_requests",
        }
    )
    AUDIT_EVENT_TYPES = frozenset(
        {
            "applications",
            "orders",
            "activities",
            "vacations",
            "blacklist",
            "config",
            "audit",
        }
    )
    REVIEW_ITEM_ALIASES = {
        "blacklist_removal_requests": "blacklist_removals",
        "verification": "verification_requests",
    }
    AUDIT_EVENT_ALIASES = {
        "config_changes": "config",
        "audit_events": "audit",
    }

    async def get_dashboard_summary(self) -> dict:
        async with get_session() as session:
            repo = AdminRepository(session)
            counts = await repo.get_dashboard_summary_counts()

        pending_total = (
            counts["applications_pending"]
            + counts["orders_pending"]
            + counts["activities_pending"]
            + counts["vacations_pending"]
            + counts["blacklist_removal_requests_pending"]
            + counts["verification_requests_pending"]
            + counts["config_changes_pending_approval"]
        )
        return {
            "generated_at": datetime.now(timezone.utc),
            "applications": {
                "total": counts["applications_total"],
                "pending": counts["applications_pending"],
            },
            "orders": {
                "total": counts["orders_total"],
                "pending": counts["orders_pending"],
            },
            "activities": {
                "total": counts["activities_total"],
                "pending": counts["activities_pending"],
            },
            "vacations": {
                "total": counts["vacations_total"],
                "pending": counts["vacations_pending"],
            },
            "blacklist_removal_requests": {
                "total": counts["blacklist_removal_requests_total"],
                "pending": counts["blacklist_removal_requests_pending"],
            },
            "verification_requests": {
                "total": counts["verification_requests_total"],
                "pending": counts["verification_requests_pending"],
            },
            "config_changes_pending_approval": counts["config_changes_pending_approval"],
            "review_queue_pending_total": pending_total,
        }

    async def list_review_queue(
        self,
        *,
        item_types: list[str] | None,
        status: str | None,
        search: str | None,
        pending_only: bool,
        limit: int,
        offset: int,
    ) -> dict:
        normalized_item_types = self._normalize_item_types(item_types)
        fetch_size = max(limit + offset, limit, 1)

        async with get_session() as session:
            repo = AdminRepository(session)
            all_items = await repo.list_review_queue_items(
                item_types=normalized_item_types,
                status=status.strip().lower() if status else None,
                search=search,
                pending_only=pending_only,
                fetch_size=fetch_size,
            )

        total = len(all_items)
        return {
            "total": total,
            "items": all_items[offset : offset + limit],
        }

    async def list_audit_timeline(
        self,
        *,
        event_types: list[str] | None,
        actor_user_id: int | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        normalized_event_types = self._normalize_event_types(event_types)
        fetch_size = max(limit + offset, limit, 1)

        async with get_session() as session:
            repo = AdminRepository(session)
            all_events = await repo.list_audit_timeline_events(
                event_types=normalized_event_types,
                actor_user_id=actor_user_id,
                search=search,
                fetch_size=fetch_size,
            )

        total = len(all_events)
        return {
            "total": total,
            "items": all_events[offset : offset + limit],
        }

    def _normalize_item_types(self, item_types: list[str] | None) -> set[str]:
        if not item_types:
            return set(self.REVIEW_ITEM_TYPES)
        normalized: set[str] = set()
        for raw in item_types:
            value = raw.strip().lower().replace("-", "_")
            if not value:
                continue
            mapped = self.REVIEW_ITEM_ALIASES.get(value, value)
            if mapped not in self.REVIEW_ITEM_TYPES:
                raise ApiException(
                    status_code=422,
                    error_code="INVALID_REVIEW_ITEM_TYPE",
                    message=f"Unknown review queue item type: {raw}",
                    details={"allowed_values": sorted(self.REVIEW_ITEM_TYPES)},
                )
            normalized.add(mapped)
        if not normalized:
            raise ApiException(
                status_code=422,
                error_code="REVIEW_ITEM_TYPE_REQUIRED",
                message="At least one valid item_types value is required",
                details={"allowed_values": sorted(self.REVIEW_ITEM_TYPES)},
            )
        return normalized

    def _normalize_event_types(self, event_types: list[str] | None) -> set[str]:
        if not event_types:
            return set(self.AUDIT_EVENT_TYPES)
        normalized: set[str] = set()
        for raw in event_types:
            value = raw.strip().lower().replace("-", "_")
            if not value:
                continue
            mapped = self.AUDIT_EVENT_ALIASES.get(value, value)
            if mapped not in self.AUDIT_EVENT_TYPES:
                raise ApiException(
                    status_code=422,
                    error_code="INVALID_AUDIT_EVENT_TYPE",
                    message=f"Unknown audit timeline event type: {raw}",
                    details={"allowed_values": sorted(self.AUDIT_EVENT_TYPES)},
                )
            normalized.add(mapped)
        if not normalized:
            raise ApiException(
                status_code=422,
                error_code="AUDIT_EVENT_TYPE_REQUIRED",
                message="At least one valid event_types value is required",
                details={"allowed_values": sorted(self.AUDIT_EVENT_TYPES)},
            )
        return normalized
