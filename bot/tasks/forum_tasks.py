"""
Celery tasks for forum operations (watching topics, fetching scores).
"""

import logging

from bot.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def watch_topic(self, topic_type: str = "orders"):
    """
    Check a forum topic for new posts.

    This task is triggered by Celery Beat every minute.
    The actual new-post notification is pushed to Redis Stream
    for the Discord bot to pick up and relay to the channel.
    """
    import asyncio
    from bot.core.redis import RedisManager

    async def _run():
        from bot.config import get_settings

        settings = get_settings()
        await RedisManager.initialize(settings.REDIS_URL)

        from bot.cloudflare.session_manager import SessionManager
        from bot.cloudflare.http_client import HttpClient

        sm = SessionManager()
        sm.set_redis(RedisManager)
        client = HttpClient(sm)

        from bot.services.forum_service import ForumService

        forum = ForumService(client, RedisManager)

        # Topic numbers would come from config/DB
        topic_map = {
            "orders": None,  # Set actual topic numbers
            "recruitment": None,
        }

        topic_number = topic_map.get(topic_type)
        if not topic_number:
            logger.warning(f"No topic number configured for: {topic_type}")
            return None

        result = await forum.watch_for_new_posts(topic_number)

        if result and result is not False:
            # Push to Redis Stream for bot to consume
            from bot.core.ipc import IPCManager

            ipc = IPCManager()
            await ipc.push_event(
                f"forum_new_post_{topic_type}",
                {"topic": topic_number, "data": result},
            )
            return {"new_post": True, "topic": topic_number}

        return {"new_post": False, "topic": topic_number}

    return asyncio.run(_run())


@celery_app.task(bind=True, max_retries=2)
def fetch_cop_scores(self):
    """Fetch live COP scores and push to Redis Stream."""
    import asyncio
    from bot.core.redis import RedisManager

    async def _run():
        from bot.config import get_settings

        settings = get_settings()
        await RedisManager.initialize(settings.REDIS_URL)

        from bot.cloudflare.session_manager import SessionManager
        from bot.cloudflare.http_client import HttpClient

        sm = SessionManager()
        sm.set_redis(RedisManager)
        client = HttpClient(sm)

        from bot.services.scraper_service import ScraperService

        scraper = ScraperService(client)
        scores = await scraper.fetch_cop_live_scores()

        if scores:
            from bot.core.ipc import IPCManager

            ipc = IPCManager()
            await ipc.push_event("cop_scores_updated", {"scores": scores})

        return scores

    return asyncio.run(_run())
