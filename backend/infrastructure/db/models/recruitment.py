from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="submitted", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    applicant_discord_id: Mapped[int | None] = mapped_column(BigInteger)
    player_id: Mapped[int | None] = mapped_column(Integer)
    submitter_type: Mapped[str] = mapped_column(String(32), default="guest", nullable=False)
    submitter_ip_hash: Mapped[str | None] = mapped_column(String(255))
    in_game_nickname: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    mta_serial: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    english_skill: Mapped[int] = mapped_column(Integer, nullable=False)
    has_second_account: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    second_account_name: Mapped[str | None] = mapped_column(String(255))
    cit_journey: Mapped[str] = mapped_column(Text, nullable=False)
    former_groups_reason: Mapped[str] = mapped_column(Text, nullable=False)
    why_join: Mapped[str] = mapped_column(Text, nullable=False)
    punishlog_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    stats_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    history_url: Mapped[str] = mapped_column(String(1024), nullable=False)


class ApplicationDecision(Base):
    __tablename__ = "application_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reviewer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    reapply_policy: Mapped[str] = mapped_column(
        String(32),
        default="allow_immediate",
        nullable=False,
    )
    cooldown_days: Mapped[int | None] = mapped_column(Integer)
    reapply_allowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ApplicationEligibilityState(Base):
    __tablename__ = "application_eligibility_state"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_application_eligibility_player_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int | None] = mapped_column(Integer)
    account_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    eligibility_status: Mapped[str] = mapped_column(
        String(64),
        default="allowed",
        nullable=False,
    )
    wait_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(
        String(64),
        default="decision_policy",
        nullable=False,
    )
    source_ref_id: Mapped[str | None] = mapped_column(String(128))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
