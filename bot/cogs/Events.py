import logging
import sys
import traceback
from datetime import datetime, timezone

import discord
from discord.ext import commands

from bot.core.redis import RedisManager
from .Voting import VotingView

ERROR_CHANNEL_ID = 1454840918418129069

logger = logging.getLogger(__name__)


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.bot.user} is ready and online")
        self.bot.add_view(VotingView())
        logger.info("VotingView registered as persistent view")

    @commands.Cog.listener()
    async def on_disconnect(self):
        logger.info("Bot disconnected (Redis connection will persist)")

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(f"Error in {event_method}: {exc_value}")
        traceback.print_exc()

        try:
            error_channel = await self.bot.fetch_channel(ERROR_CHANNEL_ID)
            embed = discord.Embed(
                title="Bot Error Detected",
                description=f"An error occurred in event: `{event_method}`",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Error Type", value=f"```{exc_type.__name__}```", inline=False)

            error_message = str(exc_value)[:1024]
            embed.add_field(name="Error Message", value=f"```{error_message}```", inline=False)

            tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            if len(tb_text) > 1010:
                tb_text = "..." + tb_text[-1007:]
            embed.add_field(name="Traceback", value=f"```python\n{tb_text}\n```", inline=False)
            embed.set_footer(text=f"Event: {event_method}")
            await error_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send error to Discord: {e}")

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        logger.error(f"Command Error in /{ctx.command.name}: {error}")
        traceback.print_exc()

        try:
            error_channel = await self.bot.fetch_channel(ERROR_CHANNEL_ID)
            embed = discord.Embed(
                title="Command Error",
                description=f"An error occurred in command: `/{ctx.command.name}`",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Command", value=f"```/{ctx.command.name}```", inline=True)
            embed.add_field(name="User", value=f"{ctx.author.mention} ({ctx.author.id})", inline=True)
            if ctx.guild:
                embed.add_field(name="Location", value=f"{ctx.guild.name} / #{ctx.channel.name}", inline=False)
            embed.add_field(name="Error Type", value=f"```{type(error).__name__}```", inline=False)

            error_message = str(error)[:1024]
            embed.add_field(name="Error Message", value=f"```{error_message}```", inline=False)

            if hasattr(error, "__traceback__"):
                tb_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
                if len(tb_text) > 1010:
                    tb_text = "..." + tb_text[-1007:]
                embed.add_field(name="Traceback", value=f"```python\n{tb_text}\n```", inline=False)

            embed.set_footer(text=f"Command: /{ctx.command.name}")
            await error_channel.send(embed=embed)

            try:
                await ctx.respond("An error occurred. The error has been logged.", ephemeral=True)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Failed to send command error to Discord: {e}")

    @commands.Cog.listener()
    async def on_resume(self):
        logger.info("Bot resumed session")
        if not RedisManager._client:
            logger.warning("Redis connection lost, re-initializing...")
            await RedisManager.initialize()
            logger.info("Redis reconnected")


def setup(bot):
    bot.add_cog(Events(bot))
