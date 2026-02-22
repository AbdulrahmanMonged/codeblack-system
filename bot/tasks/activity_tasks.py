"""
Celery tasks for activity tracking and aggregation.
"""

import logging
from datetime import datetime

from bot.core.celery_app import celery_app
from bot.tasks.async_runner import run_async

logger = logging.getLogger(__name__)


@celery_app.task
def aggregate_daily():
    """
    Aggregate daily activity stats and push summary to Redis Stream.
    Runs at 00:05 UTC via Celery Beat.
    """
    from bot.core.redis import RedisManager

    async def _run():
        from bot.config import get_settings

        settings = get_settings()
        await RedisManager.initialize(settings.REDIS_URL)

        from bot.core.database import DatabaseManager, get_session
        from bot.repositories.activity_repo import ActivityRepository

        await DatabaseManager.initialize()

        month = datetime.utcnow().strftime("%Y-%m")

        async with get_session() as session:
            repo = ActivityRepository(session)
            stats = await repo.get_monthly_stats(month)

        logger.info(f"Daily aggregation for {month}: {stats}")

        from bot.core.ipc import IPCManager

        ipc = IPCManager()
        await ipc.push_event("activity_daily_summary", stats)

        return stats

    return run_async(_run())


@celery_app.task
def check_inactive_players(days_threshold: int = 7):
    """Check for inactive players and push alerts."""
    from bot.core.redis import RedisManager

    async def _run():
        from bot.config import get_settings

        settings = get_settings()
        await RedisManager.initialize(settings.REDIS_URL)

        from bot.core.database import DatabaseManager, get_session
        from bot.repositories.activity_repo import ActivityRepository

        await DatabaseManager.initialize()

        async with get_session() as session:
            repo = ActivityRepository(session)
            inactive = await repo.get_inactive_players(days_threshold)

        if inactive:
            from bot.core.ipc import IPCManager

            ipc = IPCManager()
            await ipc.push_event(
                "inactive_players_alert",
                {"threshold_days": days_threshold, "players": inactive},
            )

        return {"count": len(inactive), "players": inactive}

    return run_async(_run())
