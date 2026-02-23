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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.db.base import Base, TimestampMixin


class UserGameAccount(TimestampMixin, Base):
    __tablename__ = "user_game_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    discord_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    mta_serial: Mapped[str | None] = mapped_column(String(64), index=True)
    forum_url: Mapped[str | None] = mapped_column(String(1024))
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    submitted_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    discord_user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    ingame_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    completed_orders: Mapped[str] = mapped_column(Text, nullable=False)
    proof_file_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    proof_file_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    proof_content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    proof_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="submitted", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
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


class OrderReview(Base):
    __tablename__ = "order_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reviewer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
