from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .player import Player


class PlayerActivity(TimestampMixin, Base):
    __tablename__ = "player_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(255), nullable=False)

    # Session
    login_time: Mapped[datetime] = mapped_column(nullable=False, index=True)
    logout_time: Mapped[datetime | None] = mapped_column(index=True)
    session_duration: Mapped[int | None] = mapped_column(Integer)  # seconds

    # Time filters
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Extra data
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    # FK
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )

    # Relationship
    player: Mapped[Player | None] = relationship(
        "Player",
        back_populates="activity_sessions",
    )

    def __repr__(self) -> str:
        return (
            f"<PlayerActivity(id={self.id}, account='{self.account_name}', "
            f"login={self.login_time}, duration={self.session_duration}s)>"
        )
