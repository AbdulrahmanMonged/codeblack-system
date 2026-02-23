from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.db.base import Base


class GroupActivity(Base):
    __tablename__ = "group_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    approved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approval_comment: Mapped[str | None] = mapped_column(Text)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    forum_topic_id: Mapped[str | None] = mapped_column(String(255))
    forum_post_id: Mapped[str | None] = mapped_column(String(255))
    publish_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    last_publish_error: Mapped[str | None] = mapped_column(Text)
    last_publish_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ActivityParticipant(Base):
    __tablename__ = "activity_participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("group_activities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("playerbase.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    participant_role: Mapped[str] = mapped_column(String(32), default="participant", nullable=False)
    attendance_status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
