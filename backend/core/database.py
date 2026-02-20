import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import get_settings
from backend.infrastructure.db.base import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Async SQLAlchemy manager for backend services."""

    _engine = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    async def initialize(cls) -> None:
        if cls._engine is not None:
            return

        settings = get_settings()
        cls._engine = create_async_engine(
            settings.database_url,
            echo=settings.BACKEND_DATABASE_ECHO,
            pool_size=settings.BACKEND_DATABASE_POOL_SIZE,
            max_overflow=settings.BACKEND_DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        cls._session_factory = async_sessionmaker(
            cls._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Ensure model modules are imported before metadata usage.
        from backend.infrastructure.db import models  # noqa: F401

        if settings.BACKEND_AUTO_CREATE_TABLES:
            async with cls._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Backend tables ensured")

    @classmethod
    async def close(cls) -> None:
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("Database engine closed")

    @classmethod
    def session_factory(cls) -> async_sessionmaker[AsyncSession]:
        if cls._session_factory is None:
            raise RuntimeError(
                "Database manager is not initialized. Call initialize() first."
            )
        return cls._session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_maker = DatabaseManager.session_factory()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

