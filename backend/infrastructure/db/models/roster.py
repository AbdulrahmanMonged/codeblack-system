from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.db.base import Base, TimestampMixin


class GroupRank(TimestampMixin, Base):
    __tablename__ = "group_ranks"
    __table_args__ = (
        UniqueConstraint("name", name="uq_rank_name"),
        UniqueConstraint("level", name="uq_rank_level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )


class Playerbase(TimestampMixin, Base):
    __tablename__ = "playerbase"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_player_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    ingame_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    mta_serial: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    country_code: Mapped[str | None] = mapped_column(String(2))


class GroupMembership(TimestampMixin, Base):
    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_group_membership_player_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("playerbase.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    joined_at: Mapped[date | None] = mapped_column(Date)
    left_at: Mapped[date | None] = mapped_column(Date)
    current_rank_id: Mapped[int | None] = mapped_column(
        ForeignKey("group_ranks.id", ondelete="SET NULL")
    )


class GroupRoster(Base):
    __tablename__ = "group_roster"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_membership_id: Mapped[int] = mapped_column(
        ForeignKey("group_memberships.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    display_rank: Mapped[str | None] = mapped_column(String(255))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_on_leave: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
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


class PlayerPunishment(Base):
    __tablename__ = "player_punishments"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("playerbase.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    punishment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    issued_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
