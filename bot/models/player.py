from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .activity import PlayerActivity
    from .event import Event


class Player(TimestampMixin, Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str | None] = mapped_column(String(255))
    account_name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    rank: Mapped[str | None] = mapped_column(String(100))
    mta_serial: Mapped[str | None] = mapped_column(String(255))
    last_online: Mapped[datetime | None] = mapped_column()
    warning_level: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_rank_change: Mapped[datetime | None] = mapped_column()
    discord_id: Mapped[int | None] = mapped_column(BigInteger)
    is_in_group: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    is_blacklisted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Relationships
    events_as_actor: Mapped[list[Event]] = relationship(
        "Event",
        foreign_keys="Event.actor_id",
        back_populates="actor",
        lazy="selectin",
    )
    events_as_target: Mapped[list[Event]] = relationship(
        "Event",
        foreign_keys="Event.target_id",
        back_populates="target",
        lazy="selectin",
    )
    activity_sessions: Mapped[list[PlayerActivity]] = relationship(
        "PlayerActivity",
        back_populates="player",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Player(id={self.id}, account_name='{self.account_name}', rank='{self.rank}')>"
