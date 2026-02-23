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


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_user_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DiscordRole(TimestampMixin, Base):
    __tablename__ = "discord_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_role_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color_int: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Permission(TimestampMixin, Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )


class DiscordRolePermission(Base):
    __tablename__ = "discord_role_permissions"
    __table_args__ = (
        UniqueConstraint("discord_role_id", "permission_key", name="uq_role_permission"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("discord_roles.discord_role_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_key: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("permissions.key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UserDiscordRole(Base):
    __tablename__ = "user_discord_roles"
    __table_args__ = (UniqueConstraint("user_id", "discord_role_id", name="uq_user_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    discord_role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("discord_roles.discord_role_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UserPermission(Base):
    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_id", "permission_key", name="uq_user_permission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_key: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("permissions.key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    allow: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_jti: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip_address: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
