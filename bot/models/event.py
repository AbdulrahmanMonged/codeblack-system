from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .player import Player


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[time] = mapped_column(Time, nullable=False)

    # Actor (who performed the action)
    actor_nickname: Mapped[str | None] = mapped_column(String(255))
    actor_account_name: Mapped[str | None] = mapped_column(String(255), index=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), index=True
    )

    # Target (who received the action)
    target_nickname: Mapped[str | None] = mapped_column(String(255))
    target_account_name: Mapped[str | None] = mapped_column(String(255), index=True)
    target_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), index=True
    )

    # Action
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    details: Mapped[dict | None] = mapped_column(JSONB)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_system_action: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Relationships
    actor: Mapped[Player | None] = relationship(
        "Player",
        foreign_keys=[actor_id],
        back_populates="events_as_actor",
    )
    target: Mapped[Player | None] = relationship(
        "Player",
        foreign_keys=[target_id],
        back_populates="events_as_target",
    )

    def __repr__(self) -> str:
        return (
            f"<Event(id={self.id}, action='{self.action_type}', "
            f"actor='{self.actor_account_name}', target='{self.target_account_name}')>"
        )
