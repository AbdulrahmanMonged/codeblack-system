"""
Celery tasks for maintenance operations (session refresh, cleanup).
"""

import logging
from datetime import datetime, timedelta

from bot.core.celery_app import celery_app
from bot.tasks.async_runner import run_async

logger = logging.getLogger(__name__)


@celery_app.task
def refresh_session():
    """
    Pre-emptively refresh the Cloudflare session.
    Runs every 12 hours via Celery Beat.
    """
    from bot.core.redis import RedisManager

    async def _run():
        from bot.config import get_settings

        settings = get_settings()
        await RedisManager.initialize(settings.REDIS_URL)

        from bot.cloudflare.session_manager import SessionManager

        sm = SessionManager()
        sm.set_redis(RedisManager)

        result = await sm.get_session(force_refresh=True)
        success = result is not None

        logger.info(f"Session refresh: {'success' if success else 'failed'}")
        return {"success": success}

    return run_async(_run())


@celery_app.task
def cleanup_stale_sessions():
    """
    Close any player activity sessions that have been open for too long
    (e.g., bot missed a logout event).
    """
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
            active = await repo.get_active_sessions()

            closed = 0
            cutoff = datetime.utcnow() - timedelta(hours=24)

            for activity_session in active:
                if activity_session.login_time < cutoff:
                    await repo.end_session(
                        activity_session.account_name,
                        activity_session.login_time + timedelta(hours=12),
                    )
                    closed += 1

        logger.info(f"Closed {closed} stale sessions")
        return {"closed": closed}

    return run_async(_run())
