from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.db.base import Base


class BlacklistEntry(Base):
    __tablename__ = "blacklist_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    blacklist_player_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    blacklist_sequence: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )
    suffix_key: Mapped[str] = mapped_column(String(16), nullable=False)
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("playerbase.id", ondelete="SET NULL"),
        index=True,
    )
    blacklist_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    identity: Mapped[str] = mapped_column(String(255), nullable=False)
    serial: Mapped[str | None] = mapped_column(String(64))
    roots: Mapped[str | None] = mapped_column(String(2))
    remarks: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    removed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BlacklistHistory(Base):
    __tablename__ = "blacklist_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    blacklist_entry_id: Mapped[int] = mapped_column(
        ForeignKey("blacklist_entries.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    change_set: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class BlacklistRemovalRequest(Base):
    __tablename__ = "blacklist_removal_requests"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_blacklist_removal_request_public_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    blacklist_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("blacklist_entries.id", ondelete="SET NULL"),
        index=True,
    )
    account_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    request_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    review_comment: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
