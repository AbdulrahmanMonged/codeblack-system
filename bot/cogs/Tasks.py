import logging

import discord
from discord.ext import commands, tasks

from bot.core.redis import RedisManager
from bot.image_generator import generate_cop_live_scores_image

logger = logging.getLogger(__name__)

TOP_SCORES_LIVE_CHANNEL_ID = 1454854877716025529


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watch_cop_live_scores.start()

    def cog_unload(self):
        logger.info("Stopping Tasks cog...")
        for task in [self.watch_cop_live_scores]:
            if task.is_running():
                task.cancel()

    async def _clear_channel_messages(self, channel: discord.abc.GuildChannel) -> int:
        """Best-effort deletion of all deletable messages in the target channel."""
        deleted = 0
        try:
            async for message in channel.history(limit=None):
                try:
                    await message.delete()
                    deleted += 1
                except discord.Forbidden:
                    logger.error("Missing permissions to delete messages in channel %s", channel.id)
                    break
                except discord.NotFound:
                    continue
                except discord.HTTPException as exc:
                    logger.debug("Skipping message %s delete due to HTTP error: %s", message.id, exc)
        except discord.Forbidden:
            logger.error("Missing permissions to read history for channel %s", channel.id)
        except Exception as exc:
            logger.error("Failed to clear channel %s: %s", channel.id, exc)
        return deleted

    @tasks.loop(seconds=30.0)
    async def watch_cop_live_scores(self):
        """Watch for cop live scores and update Discord image"""
        scraper_service = getattr(self.bot, "scraper_service", None)
        if scraper_service is None:
            logger.debug("Skipping cop score tick: scraper service not initialized")
            return

        redis_key = f"REDACTED:cop_scores:{TOP_SCORES_LIVE_CHANNEL_ID}:msg_id"

        try:
            scores = await scraper_service.fetch_cop_live_scores()
            if not scores:
                return

            channel = self.bot.get_channel(TOP_SCORES_LIVE_CHANNEL_ID)
            if not channel:
                return

            image_binary = generate_cop_live_scores_image(scores)
            stored_msg_id = await RedisManager.get(redis_key)

            if stored_msg_id:
                try:
                    message = await channel.fetch_message(int(stored_msg_id))
                    image_binary.seek(0)
                    file = discord.File(fp=image_binary, filename="cop_live_scores.png")
                    await message.edit(attachments=[], files=[file])
                    return
                except discord.NotFound:
                    logger.warning(
                        "Stored live-scores message %s not found; purging channel and recreating",
                        stored_msg_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed editing live-scores message %s (%s); purging channel and recreating",
                        stored_msg_id,
                        exc,
                    )

                deleted_count = await self._clear_channel_messages(channel)
                if deleted_count:
                    logger.info(
                        "Cleared %s message(s) from live-scores channel %s before recreating update post",
                        deleted_count,
                        channel.id,
                    )
            else:
                logger.info(
                    "No live-scores message key found for channel %s; purging before initial post",
                    channel.id,
                )
                deleted_count = await self._clear_channel_messages(channel)
                if deleted_count:
                    logger.info(
                        "Cleared %s message(s) from live-scores channel %s before initial post",
                        deleted_count,
                        channel.id,
                    )

            image_binary.seek(0)
            file = discord.File(fp=image_binary, filename="cop_live_scores.png")
            message = await channel.send(content="Top Cop Live Scores", file=file)
            await RedisManager.set(redis_key, str(message.id))

        except Exception as e:
            logger.error(f"Error in watch_cop_live_scores: {e}")

    @watch_cop_live_scores.before_loop
    async def before_watch_cop_live_scores(self):
        await self.bot.wait_until_ready()
        logger.info("Cop live scores watcher task started!")



def setup(bot):
    bot.add_cog(Tasks(bot))
