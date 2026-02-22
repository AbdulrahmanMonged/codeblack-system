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
                except discord.NotFound:
                    image_binary.seek(0)
                    file = discord.File(fp=image_binary, filename="cop_live_scores.png")
                    message = await channel.send(content="Top Cop Live Scores", file=file)
                    await RedisManager.set(redis_key, str(message.id))
                except Exception:
                    image_binary.seek(0)
                    file = discord.File(fp=image_binary, filename="cop_live_scores.png")
                    message = await channel.send(content="Top Cop Live Scores", file=file)
                    await RedisManager.set(redis_key, str(message.id))
            else:
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
