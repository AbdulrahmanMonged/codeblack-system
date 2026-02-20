import logging
from datetime import datetime

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class ActivityCommands(commands.Cog):
    """Slash commands for querying player activity data."""

    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="activity", description="Get activity stats for a player")
    @discord.option("account_name", description="Player's account name", required=True)
    @discord.option("month", description="Month to filter (YYYY-MM format)", required=False)
    async def activity(self, ctx: discord.ApplicationContext, account_name: str, month: str = None):
        await ctx.defer()

        try:
            activity_service = self.bot.activity_service
            player_service = self.bot.player_service

            player = await player_service.get_by_account_name(account_name)
            if not player:
                await ctx.followup.send(f"Player `{account_name}` not found in database.")
                return

            stats = await activity_service.get_player_total(account_name, month)

            embed = discord.Embed(
                title=f"Activity Stats: {player.nickname or account_name}",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Account Name", value=account_name, inline=True)
            if player.rank:
                embed.add_field(name="Rank", value=player.rank, inline=True)
            if month:
                embed.add_field(name="Month", value=month, inline=True)

            embed.add_field(
                name="Total Activity",
                value=f"**{stats['total_hours']:.2f}** hours ({stats['total_days']:.2f} days)",
                inline=False,
            )
            embed.add_field(name="Sessions", value=f"{stats['session_count']} sessions", inline=True)

            if stats["session_count"] > 0:
                avg_hours = stats["average_session_seconds"] / 3600
                embed.add_field(name="Avg Session", value=f"{avg_hours:.2f} hours", inline=True)

            embed.set_footer(text=f"Requested by {ctx.user.display_name}")
            embed.timestamp = datetime.now()
            await ctx.followup.send(embed=embed)

        except Exception as e:
            await ctx.followup.send(f"Error: {str(e)}")
            logger.error(f"Error in /activity command: {e}", exc_info=True)

    @discord.slash_command(name="activity-leaderboard", description="Show activity leaderboard")
    @discord.option("month", description="Month to filter (YYYY-MM format)", required=False)
    @discord.option("limit", description="Number of players to show (default: 10)", required=False, default=10)
    async def activity_leaderboard(self, ctx: discord.ApplicationContext, month: str = None, limit: int = 10):
        await ctx.defer()

        try:
            activity_service = self.bot.activity_service
            players = await activity_service.get_all_players_summary(month)

            if not players:
                await ctx.followup.send("No activity data found.")
                return

            players = players[:limit]
            title = "Activity Leaderboard"
            if month:
                title += f" - {month}"

            embed = discord.Embed(title=title, color=discord.Color.gold())

            leaderboard_text = ""
            for i, player in enumerate(players, 1):
                medal = {1: "1.", 2: "2.", 3: "3."}.get(i, f"**{i}.**")
                nickname = player["nickname"] or player["account_name"]
                hours = player["total_hours"]
                sessions = player["session_count"]
                leaderboard_text += f"{medal} **{nickname}**\n   {hours:.1f}h ({sessions} sessions)\n"

            embed.description = leaderboard_text
            embed.set_footer(text=f"{'Month: ' + month + ' | ' if month else 'All time | '}Requested by {ctx.user.display_name}")
            embed.timestamp = datetime.now()
            await ctx.followup.send(embed=embed)

        except Exception as e:
            await ctx.followup.send(f"Error: {str(e)}")
            logger.error(f"Error in /activity-leaderboard: {e}", exc_info=True)

    @discord.slash_command(name="inactive-players", description="Show inactive players")
    @discord.option("days", description="Days of inactivity threshold (default: 7)", required=False, default=7)
    async def inactive_players(self, ctx: discord.ApplicationContext, days: int = 7):
        await ctx.defer()

        try:
            activity_service = self.bot.activity_service
            players = await activity_service.get_inactive_players(days)

            if not players:
                await ctx.followup.send("No inactive players found!")
                return

            title = f"Inactive Players (No activity in {days} days)"
            embed = discord.Embed(title=title, color=discord.Color.orange())

            inactive_text = ""
            for player in players[:20]:
                nickname = player["nickname"] or player["account_name"]
                days_since = player.get("days_since_activity", "?")
                inactive_text += f"- **{nickname}** - Last seen {days_since} days ago\n"

            embed.description = inactive_text
            embed.add_field(name="Total Inactive", value=f"{len(players)} players", inline=False)
            embed.set_footer(text=f"Requested by {ctx.user.display_name}")
            embed.timestamp = datetime.now()
            await ctx.followup.send(embed=embed)

        except Exception as e:
            await ctx.followup.send(f"Error: {str(e)}")
            logger.error(f"Error in /inactive-players: {e}", exc_info=True)

    @discord.slash_command(name="monthly-stats", description="Show monthly activity statistics")
    @discord.option("month", description="Month to query (YYYY-MM format, defaults to current)", required=False)
    async def monthly_stats(self, ctx: discord.ApplicationContext, month: str = None):
        await ctx.defer()

        try:
            if not month:
                month = datetime.now().strftime("%Y-%m")

            activity_service = self.bot.activity_service
            stats = await activity_service.get_monthly_stats(month)

            embed = discord.Embed(title=f"Monthly Statistics - {month}", color=discord.Color.green())
            embed.add_field(name="Unique Players", value=f"{stats['unique_players']} players", inline=True)
            embed.add_field(name="Total Sessions", value=f"{stats['total_sessions']} sessions", inline=True)
            embed.add_field(
                name="Total Activity",
                value=f"{stats['total_hours']:.1f} hours ({stats['total_days']:.1f} days)",
                inline=False,
            )
            embed.add_field(name="Average Session", value=f"{stats['average_session_hours']:.2f} hours", inline=True)

            if stats.get("first_login"):
                embed.add_field(name="First Login", value=f"<t:{int(stats['first_login'].timestamp())}:f>", inline=True)
            if stats.get("last_logout"):
                embed.add_field(name="Last Logout", value=f"<t:{int(stats['last_logout'].timestamp())}:f>", inline=True)

            embed.set_footer(text=f"Requested by {ctx.user.display_name}")
            embed.timestamp = datetime.now()
            await ctx.followup.send(embed=embed)

        except Exception as e:
            await ctx.followup.send(f"Error: {str(e)}")
            logger.error(f"Error in /monthly-stats: {e}", exc_info=True)

    @discord.slash_command(name="player-sessions", description="Show session history for a player")
    @discord.option("account_name", description="Player's account name", required=True)
    @discord.option("month", description="Month to filter (YYYY-MM format)", required=False)
    @discord.option("limit", description="Number of sessions to show (default: 10)", required=False, default=10)
    async def player_sessions(self, ctx: discord.ApplicationContext, account_name: str, month: str = None, limit: int = 10):
        await ctx.defer()

        try:
            activity_service = self.bot.activity_service
            player_service = self.bot.player_service

            sessions = await activity_service.get_player_sessions(account_name, month, limit)
            if not sessions:
                await ctx.followup.send(f"No session history found for `{account_name}`.")
                return

            player = await player_service.get_by_account_name(account_name)
            title = f"Session History: {player.nickname if player else account_name}"
            if month:
                title += f" ({month})"

            embed = discord.Embed(title=title, color=discord.Color.purple())

            sessions_text = ""
            for session in sessions:
                login_str = f"<t:{int(session.login_time.timestamp())}:f>"
                if session.logout_time and session.session_duration:
                    hours = session.session_duration / 3600
                    sessions_text += f"- {login_str} - **{hours:.2f}h**\n"
                else:
                    sessions_text += f"- {login_str} - *Ongoing*\n"

            embed.description = sessions_text
            embed.add_field(name="Total Sessions Shown", value=f"{len(sessions)} sessions", inline=False)
            embed.set_footer(text=f"Requested by {ctx.user.display_name}")
            embed.timestamp = datetime.now()
            await ctx.followup.send(embed=embed)

        except Exception as e:
            await ctx.followup.send(f"Error: {str(e)}")
            logger.error(f"Error in /player-sessions: {e}", exc_info=True)


def setup(bot):
    bot.add_cog(ActivityCommands(bot))
