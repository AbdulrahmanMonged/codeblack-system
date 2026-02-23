from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.db.base import Base, TimestampMixin


class VotingContext(TimestampMixin, Base):
    __tablename__ = "voting_contexts"
    __table_args__ = (
        UniqueConstraint(
            "context_type",
            "context_id",
            name="uq_voting_context_type_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    context_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    context_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    opened_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    closed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(Text)
    auto_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class VotingVote(Base):
    __tablename__ = "voting_votes"
    __table_args__ = (
        UniqueConstraint(
            "voting_context_id",
            "voter_user_id",
            name="uq_voting_vote_context_voter",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    voting_context_id: Mapped[int] = mapped_column(
        ForeignKey("voting_contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    voter_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    choice: Mapped[str] = mapped_column(String(16), nullable=False)
    comment_text: Mapped[str | None] = mapped_column(Text)
    cast_at: Mapped[datetime] = mapped_column(
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


class VotingEvent(Base):
    __tablename__ = "voting_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    voting_context_id: Mapped[int] = mapped_column(
        ForeignKey("voting_contexts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    vote_choice: Mapped[str | None] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
