"""
CodeBlack Discord Bot - Factory module.

Initializes the bot with all infrastructure:
- Redis (caching + IPC)
- Database (SQLAlchemy 2.0 + async sessions)
- Cloudflare session manager + HTTP client
- Service layer (player, event, activity, forum, scraper)
- IPC manager (Redis Streams + Pub/Sub for FastAPI)
"""

import logging
import asyncio
from typing import TYPE_CHECKING

from .config import get_settings
from .core.database import DatabaseManager
from .core.ipc import IPCManager
from .core.ipc_command_handler import IPCCommandHandler
from .core.redis import RedisManager
from .cloudflare.http_client import HttpClient
from .cloudflare.session_manager import SessionManager
from .logger import CustomFormatter
from .services.activity_service import ActivityService
from .services.event_service import EventService
from .services.forum_service import ForumService
from .services.player_service import PlayerService
from .services.scraper_service import ScraperService

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import discord


def create_bot() -> "discord.Bot":
    """Create and configure the Discord bot instance."""
    import discord

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = discord.Bot(
        help_command=None,
        intents=intents,
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="Codeblack Agent"
        ),
    )

    @bot.event
    async def on_connect():
        logger.info("Connected to Discord")
        settings = get_settings()
        settings = get_settings()

        # Initialize Redis
        await RedisManager.initialize()
        logger.info("Redis initialized")

        # Initialize Database
        await DatabaseManager.initialize()
        logger.info("Database initialized")

        # Initialize Cloudflare session manager + HTTP client
        session_mgr = SessionManager()
        session_mgr.set_redis(RedisManager)
        http_client = HttpClient(session_mgr)
        if settings.CF_PROXY:
            http_client.set_proxy(settings.CF_PROXY)
            logger.info("HTTP client proxy configured for Cloudflare-protected requests")
        if settings.CF_PROXY:
            http_client.set_proxy(settings.CF_PROXY)
            logger.info("HTTP client proxy configured for Cloudflare-protected requests")

        # Initialize IPC manager
        ipc = IPCManager()
        await ipc.initialize()
        logger.info("IPC streams initialized")

        # Attach infrastructure to bot for cog access
        bot.redis = RedisManager
        bot.ipc = ipc
        bot.session_manager = session_mgr
        bot.http_client = http_client

        if not hasattr(bot, "ipc_command_task") or bot.ipc_command_task.done():
            bot.ipc_command_handler = IPCCommandHandler(ipc, bot)
            bot.ipc_command_task = asyncio.create_task(
                bot.ipc_command_handler.run()
            )
            logger.info("IPC command listener started")

        # Initialize services
        bot.forum_service = ForumService(http_client, RedisManager)
        bot.scraper_service = ScraperService(http_client)
        bot.player_service = PlayerService()
        bot.activity_service = ActivityService(ipc)
        bot.event_service = EventService(ipc)

        logger.info("All services initialized")

    return bot


# Setup discord logger
_discord_logger = logging.getLogger("discord")
_discord_logger.setLevel(logging.DEBUG)
_ch = logging.StreamHandler()
_ch.setLevel(logging.DEBUG)
_ch.setFormatter(CustomFormatter())
_discord_logger.addHandler(_ch)
