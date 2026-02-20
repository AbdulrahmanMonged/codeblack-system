import logging
import time
from datetime import datetime

import discord
from discord.ext import commands, tasks

from bot.core.redis import RedisManager
from bot.image_generator import generate_online_players_image

logger = logging.getLogger(__name__)

ONLINE_PLAYERS_CHANNEL_ID = 1454854877716025529


class ColorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_online_players_image.start()

    def cog_unload(self):
        if self.update_online_players_image.is_running():
            self.update_online_players_image.cancel()

    async def _ensure_activity_sessions(self, players):
        """Check online players and create/close activity sessions as needed."""
        activity_service = self.bot.activity_service
        player_service = self.bot.player_service
        current_time = time.time()

        online_account_names = {p.get("account_name") for p in players if p.get("account_name")}

        # Check for players who went offline
        await self._check_offline_players(online_account_names, current_time)

        # Ensure all online players have sessions
        for player in players:
            account_name = player.get("account_name")
            player_name = player.get("name")
            if not account_name or not player_name:
                continue

            redis_key = f"REDACTED:activity:online:{account_name}"
            existing_data = await RedisManager.get(redis_key, as_json=True)

            if existing_data:
                existing_data["last_seen"] = current_time
                existing_data["name"] = player_name
                await RedisManager.set(redis_key, existing_data, expire=3600)
            else:
                player_data = {
                    "login_time": current_time,
                    "name": player_name,
                    "last_seen": current_time,
                    "account_name": account_name,
                }
                await RedisManager.set(redis_key, player_data, expire=3600)

                login_dt = datetime.fromtimestamp(current_time)
                try:
                    await activity_service.record_login(account_name, player_name, login_dt)
                    logger.debug(f"Created activity session for {player_name} ({account_name})")
                except Exception as e:
                    logger.warning(f"Failed to create activity session for {player_name}: {e}")

                try:
                    await player_service.get_or_create(
                        account_name, nickname=player_name, is_in_group=True, last_online=datetime.now()
                    )
                except Exception as e:
                    logger.warning(f"Failed to update player {player_name}: {e}")

    async def _check_offline_players(self, online_account_names, current_time):
        """Close sessions for players who went offline."""
        activity_service = self.bot.activity_service

        try:
            active_sessions = await activity_service.get_active_sessions()
            for session in active_sessions:
                account_name = session.account_name
                if not account_name or account_name in online_account_names:
                    continue

                redis_key = f"REDACTED:activity:online:{account_name}"
                player_data = await RedisManager.get(redis_key, as_json=True)

                if player_data:
                    login_time = player_data.get("login_time", current_time)
                    session_duration = current_time - login_time

                    await RedisManager.delete(redis_key)
                    try:
                        await activity_service.record_logout(account_name, datetime.fromtimestamp(current_time))
                    except Exception as e:
                        logger.warning(f"Failed to end session for {account_name}: {e}")

                    logger.info(
                        f"Player logged off (auto-detected): {player_data.get('name', account_name)} "
                        f"- Duration: {self._format_duration(session_duration)}"
                    )
        except Exception as e:
            logger.error(f"Error checking offline players: {e}")

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

    @tasks.loop(seconds=30.0)
    async def update_online_players_image(self):
        scraper = self.bot.scraper_service
        redis_key = f"REDACTED:online_players:{ONLINE_PLAYERS_CHANNEL_ID}:msg_id"

        try:
            players = await scraper.fetch_players_by_group(group_filter="REDACTED")
            players = players or []

            if players:
                await self._ensure_activity_sessions(players)

            image_binary = generate_online_players_image(players)

            channel = self.bot.get_channel(ONLINE_PLAYERS_CHANNEL_ID)
            if not channel:
                return

            stored_msg_id = await RedisManager.get(redis_key)

            if stored_msg_id:
                try:
                    message = await channel.fetch_message(int(stored_msg_id))
                    image_binary.seek(0)
                    file = discord.File(fp=image_binary, filename="online_players.png")
                    await message.edit(attachments=[], files=[file])
                except discord.NotFound:
                    image_binary.seek(0)
                    file = discord.File(fp=image_binary, filename="online_players.png")
                    message = await channel.send(content="Online players", file=file)
                    await RedisManager.set(redis_key, str(message.id))
                except Exception:
                    image_binary.seek(0)
                    file = discord.File(fp=image_binary, filename="online_players.png")
                    message = await channel.send(content="Online players", file=file)
                    await RedisManager.set(redis_key, str(message.id))
            else:
                image_binary.seek(0)
                file = discord.File(fp=image_binary, filename="online_players.png")
                message = await channel.send(content="Online players", file=file)
                await RedisManager.set(redis_key, str(message.id))

        except Exception as e:
            logger.error(f"Error in update_online_players_image: {e}")

    @update_online_players_image.before_loop
    async def before_update_online_players_image(self):
        await self.bot.wait_until_ready()
        logger.info("Online players image updater task started!")


def setup(bot):
    bot.add_cog(ColorCommands(bot))
