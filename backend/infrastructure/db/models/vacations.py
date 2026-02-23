from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.db.base import Base


class VacationRequest(Base):
    __tablename__ = "vacation_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("playerbase.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    requester_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    leave_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_return_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_group: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    review_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
