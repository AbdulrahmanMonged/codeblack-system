import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Existing bot models (legacy schema currently in production)
from bot.models.base import Base as BotBase

# Import all models so they register with Base.metadata
from bot.models import Player, Event, PlayerActivity  # noqa: F401

# New backend settings/models (FastAPI control plane schema)
from backend.core.config import get_settings as get_backend_settings
from backend.infrastructure.db.base import Base as BackendBase
from backend.infrastructure.db import models as backend_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = [BotBase.metadata, BackendBase.metadata]

# Override sqlalchemy.url with backend settings.
backend_settings = get_backend_settings()
database_url = backend_settings.database_url
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
