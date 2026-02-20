import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import get_settings
from bot.models.base import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Async SQLAlchemy 2.0 database manager."""

    _engine = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    async def initialize(cls) -> None:
        if cls._engine is not None:
            logger.warning("Database engine already initialized")
            return

        settings = get_settings()

        cls._engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        cls._session_factory = async_sessionmaker(
            cls._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create all tables (for dev; production uses Alembic)
        async with cls._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database engine initialized")

    @classmethod
    async def close(cls) -> None:
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("Database engine closed")

    @classmethod
    def get_session_factory(cls) -> async_sessionmaker[AsyncSession]:
        if cls._session_factory is None:
            raise RuntimeError(
                "Database not initialized. Call DatabaseManager.initialize() first."
            )
        return cls._session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session scope."""
    factory = DatabaseManager.get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
