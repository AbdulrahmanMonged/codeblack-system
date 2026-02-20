from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DashboardCountCard(BaseModel):
    total: int
    pending: int


class DashboardSummaryResponse(BaseModel):
    generated_at: datetime
    applications: DashboardCountCard
    orders: DashboardCountCard
    activities: DashboardCountCard
    vacations: DashboardCountCard
    blacklist_removal_requests: DashboardCountCard
    verification_requests: DashboardCountCard
    config_changes_pending_approval: int
    review_queue_pending_total: int


class ReviewQueueItemResponse(BaseModel):
    item_type: str
    item_id: str
    status: str
    queued_at: datetime
    title: str
    subtitle: str | None = None
    metadata: dict[str, Any] | None = None


class ReviewQueueResponse(BaseModel):
    total: int
    items: list[ReviewQueueItemResponse]


class AuditTimelineItemResponse(BaseModel):
    event_type: str
    entity_type: str
    entity_id: str
    action: str
    actor_user_id: int | None = None
    occurred_at: datetime
    summary: str
    metadata: dict[str, Any] | None = None


class AuditTimelineResponse(BaseModel):
    total: int
    items: list[AuditTimelineItemResponse]
