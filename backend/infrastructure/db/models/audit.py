from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(128), index=True)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
