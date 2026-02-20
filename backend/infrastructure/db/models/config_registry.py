from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.db.base import Base, TimestampMixin


class ConfigRegistry(TimestampMixin, Base):
    __tablename__ = "config_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    value_json: Mapped[dict[str, Any] | list[Any] | str | int | float | bool | None] = (
        mapped_column(JSONB, nullable=True)
    )
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(BigInteger)


class ConfigChangeHistory(Base):
    __tablename__ = "config_change_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    before_json: Mapped[
        dict[str, Any] | list[Any] | str | int | float | bool | None
    ] = mapped_column(JSONB)
    after_json: Mapped[
        dict[str, Any] | list[Any] | str | int | float | bool | None
    ] = mapped_column(JSONB)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    changed_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    approved_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        default="applied",
        server_default="applied",
        nullable=False,
        index=True,
    )
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

