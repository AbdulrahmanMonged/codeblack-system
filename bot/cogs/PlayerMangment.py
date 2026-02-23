import logging
import math
from datetime import datetime

import discord
from discord.ext import commands
from discord.ui import View, Button, Select

from bot.utils.parsers import has_role_or_above

logger = logging.getLogger(__name__)


class PaginationView(View):
    """Reusable pagination view for player lists."""

    def __init__(self, embeds: list[discord.Embed], timeout=180):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.max_pages = len(embeds)

        if self.max_pages <= 1:
            self.first_page.disabled = True
            self.prev_page.disabled = True
            self.next_page.disabled = True
            self.last_page.disabled = True

    def update_buttons(self):
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.max_pages - 1
        self.last_page.disabled = self.current_page >= self.max_pages - 1

    @discord.ui.button(label="First", style=discord.ButtonStyle.gray)
    async def first_page(self, button: Button, interaction: discord.Interaction):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.green)
    async def prev_page(self, button: Button, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next_page(self, button: Button, interaction: discord.Interaction):
        self.current_page = min(self.max_pages - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Last", style=discord.ButtonStyle.gray)
    async def last_page(self, button: Button, interaction: discord.Interaction):
        self.current_page = self.max_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class PlayerFilterView(View):
    """View for filtering players by rank."""

    def __init__(self, ctx, all_players: list):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.all_players = all_players

        ranks = set()
        for player in all_players:
            if player.rank:
                ranks.add(player.rank)

        options = [discord.SelectOption(label="All Ranks", value="all", default=True)]
        for rank in sorted(ranks):
            options.append(discord.SelectOption(label=rank, value=rank))

        self.rank_select.options = options[:25]

    @discord.ui.select(placeholder="Filter by rank...")
    async def rank_select(self, select: Select, interaction: discord.Interaction):
        selected_rank = select.values[0]

        if selected_rank == "all":
            filtered = self.all_players
        else:
            filtered = [p for p in self.all_players if p.rank == selected_rank]

        embeds = create_player_list_embeds(filtered, f"Players - {selected_rank}")

        if embeds:
            view = PaginationView(embeds)
            view.update_buttons()
            await interaction.response.edit_message(embed=embeds[0], view=view)
        else:
            embed = discord.Embed(
                title="No Players Found",
                description=f"No players found with rank: {selected_rank}",
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=None)


def create_player_list_embeds(players: list, title: str, per_page: int = 20) -> list[discord.Embed]:
    """Create paginated embeds for player lists."""
    if not players:
        return []

    embeds = []
    total_pages = math.ceil(len(players) / per_page)

    for page in range(total_pages):
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, len(players))
        page_players = players[start_idx:end_idx]

        embed = discord.Embed(
            title=title,
            description=f"Total: {len(players)} players",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )

        for player in page_players:
            nickname = player.nickname or "N/A"
            account_name = player.account_name
            rank = player.rank or "No Rank"
            warning = player.warning_level or 0
            in_group = "Yes" if player.is_in_group else "No"

            last_online = player.last_online
            if last_online:
                delta = datetime.now() - last_online
                if delta.days == 0:
                    last_online_str = "Today"
                elif delta.days == 1:
                    last_online_str = "Yesterday"
                elif delta.days < 7:
                    last_online_str = f"{delta.days} days ago"
                else:
                    last_online_str = last_online.strftime("%d/%m/%Y")
            else:
                last_online_str = "Unknown"

            value = (
                f"**Account:** {account_name}\n"
                f"**Rank:** {rank}\n"
                f"**Last Online:** {last_online_str}\n"
                f"**Warning:** {warning}%\n"
                f"**In Group:** {in_group}"
            )

            embed.add_field(name=nickname, value=value, inline=True)

        embed.set_footer(text=f"Page {page + 1}/{total_pages}")
        embeds.append(embed)

    return embeds


def format_timeago(dt: datetime) -> str:
    """Format datetime to human-readable time ago."""
    if not dt:
        return "Unknown"

    delta = datetime.now() - dt

    if delta.days == 0:
        if delta.seconds < 60:
            return "Just now"
        elif delta.seconds < 3600:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        else:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    elif delta.days < 30:
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif delta.days < 365:
        months = delta.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = delta.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"


class PlayerMangment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_role_or_above()
    @discord.slash_command(name="player", description="Get detailed information about a player")
    @discord.option("account_name", description="Player's account name", required=True)
    async def player_info(self, ctx: discord.ApplicationContext, account_name: str):
        """Get detailed information about a specific player."""
        await ctx.defer()

        player_service = self.bot.player_service
        event_service = self.bot.event_service

        player = await player_service.get_by_account_name(account_name)
        if not player:
            embed = discord.Embed(
                title="Player Not Found",
                description=f"No player found with account name: `{account_name}`",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        stats = await event_service.get_action_counts(player.id)

        embed = discord.Embed(
            title=f"Player Profile: {player.nickname or account_name}",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )

        embed.add_field(
            name="Basic Information",
            value=(
                f"**Account Name:** {player.account_name}\n"
                f"**Nickname:** {player.nickname or 'N/A'}\n"
                f"**Rank:** {player.rank or 'No Rank'}\n"
                f"**In Group:** {'Yes' if player.is_in_group else 'No'}"
            ),
            inline=False,
        )

        last_online_str = format_timeago(player.last_online) if player.last_online else "Unknown"
        last_rank_change_str = format_timeago(player.last_rank_change) if player.last_rank_change else "Unknown"

        embed.add_field(
            name="Activity",
            value=(
                f"**Last Online:** {last_online_str}\n"
                f"**Last Rank Change:** {last_rank_change_str}\n"
                f"**Warning Level:** {player.warning_level or 0}%"
            ),
            inline=False,
        )

        embed.add_field(
            name="Statistics",
            value=(
                f"**Actions Performed:** {stats['as_actor']}\n"
                f"**Actions Received:** {stats['as_target']}\n"
                f"**Total Activity:** {stats['total']}"
            ),
            inline=False,
        )

        if player.discord_id:
            embed.add_field(name="Discord", value=f"**Linked Account:** <@{player.discord_id}>", inline=False)

        if player.mta_serial:
            embed.add_field(name="MTA Serial", value=f"`{player.mta_serial}`", inline=False)

        embed.set_footer(text=f"Player ID: {player.id}")
        await ctx.respond(embed=embed)

    @has_role_or_above()
    @discord.slash_command(name="players", description="List all players with filtering options")
    @discord.option(
        "filter_type",
        description="Filter players by status",
        choices=["All Players", "In Group", "Left Group"],
        default="All Players",
    )
    async def list_players(self, ctx: discord.ApplicationContext, filter_type: str = "All Players"):
        """List all players with filtering."""
        await ctx.defer()

        player_service = self.bot.player_service

        if filter_type == "In Group":
            players = await player_service.get_all_in_group()
            title = "Current Group Members"
        elif filter_type == "Left Group":
            # Use get_all_in_group logic inverted - get all, filter not in group
            from bot.core.database import get_session
            from bot.repositories.player_repo import PlayerRepository

            async with get_session() as session:
                repo = PlayerRepository(session)
                players = list(await repo.get_not_in_group())
            title = "Ex-Members"
        else:
            from bot.core.database import get_session
            from bot.repositories.player_repo import PlayerRepository

            async with get_session() as session:
                repo = PlayerRepository(session)
                players = list(await repo.get_all(limit=1000))
            title = "All Players"

        if not players:
            embed = discord.Embed(
                title="No Players Found",
                description=f"No players found for filter: {filter_type}",
                color=discord.Color.orange(),
            )
            await ctx.respond(embed=embed)
            return

        players.sort(key=lambda p: p.last_online or datetime.min, reverse=True)
        embeds = create_player_list_embeds(players, title)

        if embeds:
            view = PaginationView(embeds)
            view.update_buttons()
            await ctx.respond(embed=embeds[0], view=view)

    @has_role_or_above()
    @discord.slash_command(name="player_events", description="Show recent events for a player")
    @discord.option("account_name", description="Player's account name", required=True)
    @discord.option("limit", description="Number of events to show", min_value=5, max_value=50, default=20)
    async def player_events(self, ctx: discord.ApplicationContext, account_name: str, limit: int = 20):
        """Show recent events involving a specific player."""
        await ctx.defer()

        player_service = self.bot.player_service
        event_service = self.bot.event_service

        player = await player_service.get_by_account_name(account_name)
        if not player:
            embed = discord.Embed(
                title="Player Not Found",
                description=f"No player found with account name: `{account_name}`",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        events = await event_service.get_player_events(player.id, limit=limit)
        if not events:
            embed = discord.Embed(
                title="No Events",
                description=f"No events found for player: {player.nickname or account_name}",
                color=discord.Color.orange(),
            )
            await ctx.respond(embed=embed)
            return

        embeds = []
        per_page = 10
        total_pages = math.ceil(len(events) / per_page)

        for page in range(total_pages):
            start_idx = page * per_page
            end_idx = min(start_idx + per_page, len(events))
            page_events = events[start_idx:end_idx]

            embed = discord.Embed(
                title=f"Events for {player.nickname or account_name}",
                description=f"Recent {len(events)} events",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            for event in page_events:
                timestamp_str = format_timeago(event.timestamp) if event.timestamp else "Unknown"
                action_type = event.action_type or "Unknown"
                raw_text = event.raw_text or "No description"

                if len(raw_text) > 200:
                    raw_text = raw_text[:197] + "..."

                embed.add_field(
                    name=f"{action_type.replace('_', ' ').title()} - {timestamp_str}",
                    value=raw_text,
                    inline=False,
                )

            embed.set_footer(text=f"Page {page + 1}/{total_pages}")
            embeds.append(embed)

        if embeds:
            view = PaginationView(embeds)
            view.update_buttons()
            await ctx.respond(embed=embeds[0], view=view)

    @has_role_or_above()
    @discord.slash_command(name="recent_events", description="Show recent group events")
    @discord.option(
        "event_type",
        description="Filter by event type",
        choices=["All", "Promotions", "Demotions", "Joins", "Leaves", "Kicks", "Warnings", "Bank"],
        default="All",
    )
    @discord.option("limit", description="Number of events to show", min_value=5, max_value=50, default=20)
    async def recent_events(self, ctx: discord.ApplicationContext, event_type: str = "All", limit: int = 20):
        """Show recent group events with filtering."""
        await ctx.defer()

        event_service = self.bot.event_service

        from bot.core.database import get_session
        from bot.repositories.event_repo import EventRepository

        type_mapping = {
            "Promotions": "promotion",
            "Demotions": "demotion",
            "Joins": "join",
            "Leaves": "leave",
            "Kicks": "kick",
            "Warnings": "warn",
        }

        if event_type == "All":
            events = await event_service.get_recent(limit=limit)
            title = "Recent Group Events"
        elif event_type == "Bank":
            async with get_session() as session:
                repo = EventRepository(session)
                deposits = list(await repo.get_by_type("bank_deposit", limit=limit))
                withdraws = list(await repo.get_by_type("bank_withdraw", limit=limit))
            events = sorted(deposits + withdraws, key=lambda e: e.timestamp or datetime.min, reverse=True)[:limit]
            title = "Recent Bank Transactions"
        else:
            action_type = type_mapping.get(event_type)
            async with get_session() as session:
                repo = EventRepository(session)
                events = list(await repo.get_by_type(action_type, limit=limit))
            title = f"Recent {event_type}"

        if not events:
            embed = discord.Embed(
                title="No Events",
                description=f"No events found for: {event_type}",
                color=discord.Color.orange(),
            )
            await ctx.respond(embed=embed)
            return

        embeds = []
        per_page = 10
        total_pages = math.ceil(len(events) / per_page)

        for page in range(total_pages):
            start_idx = page * per_page
            end_idx = min(start_idx + per_page, len(events))
            page_events = events[start_idx:end_idx]

            embed = discord.Embed(
                title=title,
                description=f"Showing {len(events)} events",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            for event in page_events:
                timestamp_str = format_timeago(event.timestamp) if event.timestamp else "Unknown"
                action_type = event.action_type or "Unknown"
                raw_text = event.raw_text or "No description"

                if len(raw_text) > 200:
                    raw_text = raw_text[:197] + "..."

                embed.add_field(
                    name=f"{action_type.replace('_', ' ').title()} - {timestamp_str}",
                    value=raw_text,
                    inline=False,
                )

            embed.set_footer(text=f"Page {page + 1}/{total_pages}")
            embeds.append(embed)

        if embeds:
            view = PaginationView(embeds)
            view.update_buttons()
            await ctx.respond(embed=embeds[0], view=view)

    @has_role_or_above()
    @discord.slash_command(name="group_stats", description="Show detailed statistics for the group")
    async def group_stats(self, ctx: discord.ApplicationContext):
        """Show overall group statistics."""
        await ctx.defer()

        player_service = self.bot.player_service
        event_service = self.bot.event_service

        from bot.core.database import get_session
        from bot.repositories.player_repo import PlayerRepository
        from bot.repositories.event_repo import EventRepository
        from sqlalchemy import select, func
        from bot.models.player import Player
        from bot.models.event import Event
        from datetime import timedelta

        in_group = await player_service.get_all_in_group()

        async with get_session() as session:
            repo = PlayerRepository(session)
            all_players = list(await repo.get_all())
            ex_members = list(await repo.get_not_in_group())

            # Rank distribution
            rank_stmt = (
                select(Player.rank, func.count().label("count"))
                .where(Player.rank.isnot(None), Player.is_in_group == True)
                .group_by(Player.rank)
                .order_by(func.count().desc())
            )
            rank_result = await session.execute(rank_stmt)
            rank_counts = rank_result.all()

            # Warning count
            warn_stmt = select(func.count()).where(
                Player.warning_level > 0, Player.is_in_group == True
            )
            warn_result = await session.execute(warn_stmt)
            total_warnings = warn_result.scalar() or 0

            # Event type counts
            event_stmt = (
                select(Event.action_type, func.count().label("count"))
                .group_by(Event.action_type)
                .order_by(func.count().desc())
                .limit(10)
            )
            event_result = await session.execute(event_stmt)
            event_counts = event_result.all()

            # Recent events count (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            recent_stmt = select(func.count()).where(Event.timestamp > week_ago)
            recent_result = await session.execute(recent_stmt)
            recent_events = recent_result.scalar() or 0

        embed = discord.Embed(
            title="CodeBlack Group Statistics",
            description="Overview of group activity and members",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )

        embed.add_field(
            name="Members",
            value=(
                f"**Total Players:** {len(all_players)}\n"
                f"**Current Members:** {len(in_group)}\n"
                f"**Ex-Members:** {len(ex_members)}\n"
                f"**With Warnings:** {total_warnings}"
            ),
            inline=False,
        )

        if rank_counts:
            rank_str = "\n".join([f"**{row.rank}:** {row.count}" for row in rank_counts[:10]])
            embed.add_field(name="Rank Distribution", value=rank_str, inline=False)

        if event_counts:
            event_str = "\n".join([
                f"**{row.action_type.replace('_', ' ').title()}:** {row.count}"
                for row in event_counts
            ])
            embed.add_field(name="Top Event Types", value=event_str, inline=False)

        embed.add_field(
            name="Recent Activity",
            value=f"**Events (Last 7 Days):** {recent_events}",
            inline=False,
        )

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(PlayerMangment(bot))
