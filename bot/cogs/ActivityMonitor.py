import logging
import re
import time
from datetime import datetime

import discord
from discord.ext import commands, tasks

from bot.core.redis import RedisManager

logger = logging.getLogger(__name__)

WATCHING_CHANNEL_ID = 1434431786368241725
CIT_BOT_ID = 403112358630916096


class ActivityMonitor(commands.Cog):
    """
    Activity monitoring with multi-tier player name resolution:
    1. In-memory cache (fastest, volatile)
    2. Database lookup (persistent)
    3. Website fetch (fallback, authoritative)
    """

    def __init__(self, bot):
        self.bot = bot
        self.error_count = 0
        self.error_window_start = None
        self.max_errors = 10
        self.error_window_minutes = 15

        self.player_cache = {}
        self.cache_last_updated = 0
        self.cache_update_interval = 60

        self.monitor_player_activity.start()

    def cog_unload(self):
        self.monitor_player_activity.cancel()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != CIT_BOT_ID or message.channel.id != WATCHING_CHANNEL_ID:
            return

        content = message.content.strip()
        if content.startswith("(GROUP-DISCORD)"):
            return

        event_data = self._parse_event_message(content)
        if event_data:
            await self._handle_discord_event(event_data)

    def _parse_event_message(self, message):
        login_match = re.match(r"^(.+?)\s+has logged in\.$", message)
        if login_match:
            return {"player_name": login_match.group(1).strip(), "event_type": "login"}

        logout_match = re.match(r"^(.+?)\s+has logged off\.\s*(?:\(.*\))?$", message)
        if logout_match:
            return {"player_name": logout_match.group(1).strip(), "event_type": "logout"}

        return None

    async def _handle_discord_event(self, event_data):
        player_name = event_data["player_name"]
        event_type = event_data["event_type"]
        player_service = getattr(self.bot, "player_service", None)
        if player_service is None:
            logger.debug("Skipping discord activity event: player service not initialized")
            return

        logger.debug(f"Discord Event: {player_name} - {event_type}")

        # Tier 1: In-memory cache
        account_name = self.player_cache.get(player_name)

        if not account_name:
            # Tier 2: Database + Redis cache
            account_name = await player_service.resolve_account_name(player_name)
            if account_name:
                self.player_cache[player_name] = account_name

        if not account_name:
            # Tier 3: Website fetch
            account_name = await self._fetch_account_name_for_player(player_name)
            if not account_name:
                logger.debug(f"Skipping event for {player_name} - no account_name found")
                return

        if event_type == "login":
            await self._handle_login(player_name, account_name)
        elif event_type == "logout":
            await self._handle_logout(player_name, account_name)

    async def _update_player_cache(self):
        current_time = time.time()
        if current_time - self.cache_last_updated < self.cache_update_interval:
            return

        scraper = getattr(self.bot, "scraper_service", None)
        player_service = getattr(self.bot, "player_service", None)
        if scraper is None or player_service is None:
            logger.debug("Skipping player cache refresh: services are not initialized")
            return

        result = await scraper.fetch_players_by_group(group_filter="REDACTED")
        if not result:
            return

        new_cache = {}
        for player in result:
            player_name = player["name"]
            account_name = player["account_name"]
            new_cache[player_name] = account_name

            await player_service.get_or_create(
                account_name, nickname=player_name, is_in_group=True, last_online=datetime.now()
            )
            await player_service.cache_nickname_mapping(player_name, account_name)

        self.player_cache = new_cache
        self.cache_last_updated = current_time
        logger.info(f"Player cache updated ({len(new_cache)} players)")

    async def _fetch_account_name_for_player(self, player_name):
        player_service = getattr(self.bot, "player_service", None)
        scraper = getattr(self.bot, "scraper_service", None)
        if player_service is None or scraper is None:
            logger.debug("Skipping player fetch fallback: services are not initialized")
            return None

        # Try DB first
        account_name = await player_service.resolve_account_name(player_name)
        if account_name:
            self.player_cache[player_name] = account_name
            return account_name

        # Fallback: website
        result = await scraper.fetch_players_by_group(group_filter="REDACTED")
        if not result:
            return None

        for player in result:
            if player["name"] == player_name:
                acct = player["account_name"]
                await player_service.get_or_create(
                    acct, nickname=player_name, is_in_group=True, last_online=datetime.now()
                )
                await player_service.cache_nickname_mapping(player_name, acct)
                self.player_cache[player_name] = acct
                return acct

        return None

    async def _handle_login(self, player_name, account_name):
        activity_service = getattr(self.bot, "activity_service", None)
        if activity_service is None:
            logger.debug("Skipping login record: activity service not initialized")
            return

        current_time = time.time()

        redis_key = f"REDACTED:activity:online:{account_name}"
        existing_data = await RedisManager.get(redis_key, as_json=True)

        if existing_data:
            existing_data["name"] = player_name
            existing_data["last_seen"] = current_time
            await RedisManager.set(redis_key, existing_data, expire=3600)
            return

        player_data = {
            "login_time": current_time,
            "name": player_name,
            "last_seen": current_time,
            "account_name": account_name,
        }
        await RedisManager.set(redis_key, player_data, expire=3600)

        login_dt = datetime.fromtimestamp(current_time)
        logger.info(f"Player logged in: {player_name} ({account_name}) at {login_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        await activity_service.record_login(account_name, player_name, login_dt)

    async def _handle_logout(self, player_name, account_name):
        activity_service = getattr(self.bot, "activity_service", None)
        if activity_service is None:
            logger.debug("Skipping logout record: activity service not initialized")
            return

        current_time = time.time()

        redis_key = f"REDACTED:activity:online:{account_name}"
        player_data = await RedisManager.get(redis_key, as_json=True)

        if not player_data:
            return

        login_time = player_data.get("login_time", current_time)
        session_duration = current_time - login_time

        logger.info(
            f"Player logged off: {player_name} ({account_name}) - "
            f"Duration: {self._format_duration(session_duration)}"
        )

        await RedisManager.delete(redis_key)
        await activity_service.record_logout(account_name, datetime.fromtimestamp(current_time))

    @tasks.loop(seconds=60)
    async def monitor_player_activity(self):
        try:
            self.cache_last_updated = 0
            await self._update_player_cache()
            self.error_count = 0
            self.error_window_start = None
        except Exception as e:
            self._handle_error(f"Error in monitor_player_activity: {e}")

    @monitor_player_activity.before_loop
    async def before_monitor(self):
        await self.bot.wait_until_ready()
        logger.info("Player Activity Monitor started!")

    def _format_duration(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")
        return " ".join(parts)

    def _handle_error(self, error_msg):
        current_time = datetime.now()
        if self.error_window_start is None:
            self.error_window_start = current_time
            self.error_count = 0

        window_duration = (current_time - self.error_window_start).total_seconds() / 60
        if window_duration > self.error_window_minutes:
            self.error_window_start = current_time
            self.error_count = 0

        self.error_count += 1
        logger.error(f"Error ({self.error_count}/{self.max_errors}): {error_msg}")

        if self.error_count >= self.max_errors:
            logger.critical("Error limit reached. Stopping monitor task.")
            self.monitor_player_activity.cancel()



def setup(bot):
    bot.add_cog(ActivityMonitor(bot))
