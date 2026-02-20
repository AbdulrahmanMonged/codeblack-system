import logging
import sys
import traceback
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

logger = logging.getLogger(__name__)

OWNER_GUILD_ID = 1452576587047239793


class Administration(commands.Cog):
    """Administration commands for bot owners."""

    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)

    manage_cogs = SlashCommandGroup("cog", "Cog management commands", guild_ids=[OWNER_GUILD_ID])

    @manage_cogs.command(name="reload", description="Reload a specific cog")
    async def reload_cog(
        self,
        ctx: discord.ApplicationContext,
        cog_name: discord.Option(str, "Name of the cog to reload", required=True),
    ):
        await ctx.defer(ephemeral=True)

        try:
            self.bot.unload_extension(f"bot.cogs.{cog_name}")
            self.bot.load_extension(f"bot.cogs.{cog_name}")

            embed = discord.Embed(
                title="Cog Reloaded",
                description=f"Successfully reloaded cog: `{cog_name}`",
                color=discord.Color.green(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        except discord.ExtensionNotLoaded:
            embed = discord.Embed(title="Error", description=f"Cog `{cog_name}` is not loaded", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        except discord.ExtensionNotFound:
            embed = discord.Embed(title="Error", description=f"Cog `{cog_name}` not found", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="Error Reloading Cog",
                description=f"```python\n{str(e)}\n```",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @manage_cogs.command(name="load", description="Load a specific cog")
    async def load_cog(
        self,
        ctx: discord.ApplicationContext,
        cog_name: discord.Option(str, "Name of the cog to load", required=True),
    ):
        await ctx.defer(ephemeral=True)

        try:
            self.bot.load_extension(f"bot.cogs.{cog_name}")
            embed = discord.Embed(
                title="Cog Loaded",
                description=f"Successfully loaded cog: `{cog_name}`",
                color=discord.Color.green(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        except discord.ExtensionAlreadyLoaded:
            embed = discord.Embed(title="Warning", description=f"Cog `{cog_name}` is already loaded", color=discord.Color.orange())
            await ctx.respond(embed=embed, ephemeral=True)

        except discord.ExtensionNotFound:
            embed = discord.Embed(title="Error", description=f"Cog `{cog_name}` not found", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(title="Error Loading Cog", description=f"```python\n{str(e)}\n```", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

    @manage_cogs.command(name="unload", description="Unload a specific cog")
    async def unload_cog(
        self,
        ctx: discord.ApplicationContext,
        cog_name: discord.Option(str, "Name of the cog to unload", required=True),
    ):
        await ctx.defer(ephemeral=True)

        if cog_name == "Administration":
            embed = discord.Embed(title="Error", description="Cannot unload the Administration cog", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
            return

        try:
            self.bot.unload_extension(f"bot.cogs.{cog_name}")
            embed = discord.Embed(
                title="Cog Unloaded",
                description=f"Successfully unloaded cog: `{cog_name}`",
                color=discord.Color.green(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        except discord.ExtensionNotLoaded:
            embed = discord.Embed(title="Error", description=f"Cog `{cog_name}` is not loaded", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(title="Error Unloading Cog", description=f"```python\n{str(e)}\n```", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

    @manage_cogs.command(name="reloadall", description="Reload all loaded cogs")
    async def reload_all_cogs(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        loaded_cogs = list(self.bot.extensions.keys())
        success = []
        failed = []

        for cog in loaded_cogs:
            try:
                self.bot.reload_extension(cog)
                success.append(cog.split(".")[-1])
            except Exception as e:
                failed.append(f"{cog.split('.')[-1]}: {str(e)}")

        embed = discord.Embed(
            title="Reload All Cogs",
            color=discord.Color.green() if not failed else discord.Color.orange(),
        )

        if success:
            embed.add_field(
                name=f"Success ({len(success)})",
                value="\n".join(f"- `{cog}`" for cog in success),
                inline=False,
            )

        if failed:
            embed.add_field(
                name=f"Failed ({len(failed)})",
                value="\n".join(f"- {fail}" for fail in failed[:5]),
                inline=False,
            )

        await ctx.respond(embed=embed, ephemeral=True)

    @manage_cogs.command(name="list", description="List all loaded cogs")
    async def list_cogs(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        loaded_cogs = [ext.split(".")[-1] for ext in self.bot.extensions.keys()]

        embed = discord.Embed(
            title="Loaded Cogs",
            description=f"Total: **{len(loaded_cogs)}** cogs",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Cogs",
            value="\n".join(f"- `{cog}`" for cog in sorted(loaded_cogs)),
            inline=False,
        )

        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="shutdown", description="Shutdown the bot", guild_ids=[OWNER_GUILD_ID])
    async def shutdown(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title="Shutting Down", description="Bot is shutting down...", color=discord.Color.red())
        await ctx.respond(embed=embed, ephemeral=True)
        await self.bot.close()

    @discord.slash_command(name="sync", description="Sync application commands globally", guild_ids=[OWNER_GUILD_ID])
    async def sync_commands(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        try:
            await self.bot.sync_commands()
            embed = discord.Embed(
                title="Commands Synced",
                description="Application commands have been synced globally",
                color=discord.Color.green(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="Sync Failed", description=f"```python\n{str(e)}\n```", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="botinfo", description="Display bot information", guild_ids=[OWNER_GUILD_ID])
    async def botinfo(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        uptime = datetime.now(timezone.utc) - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_parts = []
        if days > 0:
            uptime_parts.append(f"{days}d")
        if hours > 0:
            uptime_parts.append(f"{hours}h")
        if minutes > 0:
            uptime_parts.append(f"{minutes}m")
        uptime_parts.append(f"{seconds}s")
        uptime_str = " ".join(uptime_parts)

        embed = discord.Embed(title="Bot Information", color=discord.Color.blue())

        embed.add_field(
            name="Bot",
            value=(
                f"**Name:** {self.bot.user.name}\n"
                f"**ID:** {self.bot.user.id}\n"
                f"**Guilds:** {len(self.bot.guilds)}"
            ),
            inline=True,
        )

        embed.add_field(
            name="System",
            value=(
                f"**Python:** {sys.version.split()[0]}\n"
                f"**Py-cord:** {discord.__version__}\n"
                f"**Loaded Cogs:** {len(self.bot.extensions)}"
            ),
            inline=True,
        )

        embed.add_field(
            name="Performance",
            value=f"**Latency:** {round(self.bot.latency * 1000)}ms\n**Uptime:** {uptime_str}",
            inline=False,
        )

        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_footer(text=f"Started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(
        name="eval",
        description="Evaluate Python code (Owner only)",
        guild_ids=[OWNER_GUILD_ID],
    )
    async def eval_code(
        self,
        ctx: discord.ApplicationContext,
        code: discord.Option(str, "Python code to evaluate", required=True),
    ):
        await ctx.defer(ephemeral=True)

        try:
            env = {"bot": self.bot, "ctx": ctx, "discord": discord, "commands": commands}
            result = eval(code, env)

            if hasattr(result, "__await__"):
                result = await result

            embed = discord.Embed(
                title="Eval Result",
                description=f"```python\n{result}\n```",
                color=discord.Color.green(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="Eval Error",
                description=f"```python\n{type(e).__name__}: {str(e)}\n```",
                color=discord.Color.red(),
            )

            tb = traceback.format_exc()
            if len(tb) < 1000:
                embed.add_field(name="Traceback", value=f"```python\n{tb}\n```", inline=False)

            await ctx.respond(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(Administration(bot))
