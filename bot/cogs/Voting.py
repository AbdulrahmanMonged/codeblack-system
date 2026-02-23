import logging

import discord
from discord.ext import commands

from bot.core.redis import RedisManager
from bot.utils.parsers import has_role_or_above

APPLICATION_REVIEWER_CHANNEL_ID = 1452611290462687244

logger = logging.getLogger(__name__)


class VotingView(discord.ui.View):
    def __init__(self, thread_id: int = None):
        super().__init__(timeout=None)
        self.thread_id = thread_id

    @staticmethod
    def get_vote_key(thread_id: int) -> str:
        return f"REDACTED:voting:thread:{thread_id}"

    @staticmethod
    def get_voters_key(thread_id: int) -> str:
        return f"REDACTED:voting:thread:{thread_id}:voters"

    @staticmethod
    def get_voter_choice_key(thread_id: int, user_id: int) -> str:
        return f"REDACTED:voting:thread:{thread_id}:voter:{user_id}"

    def get_thread_id_from_interaction(self, interaction: discord.Interaction) -> int:
        if isinstance(interaction.channel, discord.Thread):
            return interaction.channel.id
        raise ValueError("Interaction is not in a thread")

    async def update_button_labels(self, thread_id: int):
        vote_data = await RedisManager.hgetall(self.get_vote_key(thread_id))
        upvotes = vote_data.get("upvotes", "0")
        downvotes = vote_data.get("downvotes", "0")

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "vote_yes":
                    child.label = f"Yes ({upvotes})"
                elif child.custom_id == "vote_no":
                    child.label = f"No ({downvotes})"

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, custom_id="vote_yes", emoji="👍")
    async def yes_callback(self, button, interaction):
        await interaction.response.send_message(
            "Voting is now managed by the backend dashboard. Discord button voting is deprecated.",
            ephemeral=True,
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.red, custom_id="vote_no", emoji="👎")
    async def no_callback(self, button, interaction):
        await interaction.response.send_message(
            "Voting is now managed by the backend dashboard. Discord button voting is deprecated.",
            ephemeral=True,
        )


class Voting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        view = VotingView()
        self.bot.add_view(view)
        logger.info("VotingView registered as persistent view")

    async def end_voting_and_update_message(self, thread_id: int):
        vote_msg_key = f"REDACTED:voting:thread:{thread_id}:message_id"
        msg_id = await RedisManager.get(vote_msg_key)
        if not msg_id:
            return

        thread = self.bot.get_channel(thread_id)
        if not thread:
            return

        try:
            message = await thread.fetch_message(int(msg_id))
            final_content = "**Voting for this thread is managed by the backend dashboard.**"
            view = VotingView(thread_id)
            view.disable_all_items()
            await message.edit(content=final_content, view=view)
        except Exception as e:
            logger.error(f"Error updating vote message: {e}")

    async def initialize_vote(self, thread_id: int):
        _ = thread_id

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if isinstance(thread.parent, discord.ForumChannel):
            if thread.parent_id == APPLICATION_REVIEWER_CHANNEL_ID:
                starter_message = thread.starting_message or await thread.fetch_message(thread.id)
                await starter_message.reply(
                    "Voting is managed from the backend dashboard. "
                    "Discord-side vote controls are deprecated."
                )

    @has_role_or_above()
    @discord.slash_command(name="vote", description="Show current voting status for this thread")
    async def vote_command(self, ctx):
        await ctx.defer(ephemeral=True)
        await ctx.followup.send(
            "Voting is now backend-owned. Use the backend dashboard/API to view vote status.",
            ephemeral=True,
        )

    @has_role_or_above()
    @discord.slash_command(name="enable_voting", description="Re-enable voting on a closed vote")
    async def enable_voting_command(self, ctx):
        await ctx.defer(ephemeral=True)
        await ctx.followup.send(
            "Voting controls moved to backend. Use backend API `/voting/{context_type}/{context_id}/reopen`.",
            ephemeral=True,
        )

    @has_role_or_above()
    @discord.slash_command(name="disable_voting", description="Manually close voting")
    async def disable_voting_command(self, ctx):
        await ctx.defer(ephemeral=True)
        await ctx.followup.send(
            "Voting controls moved to backend. Use backend API `/voting/{context_type}/{context_id}/close`.",
            ephemeral=True,
        )

    @has_role_or_above()
    @discord.slash_command(name="reset_voting", description="Reset vote counts to 0")
    async def reset_voting_command(self, ctx):
        await ctx.defer(ephemeral=True)
        await ctx.followup.send(
            "Voting controls moved to backend. Use backend API `/voting/{context_type}/{context_id}/reset`.",
            ephemeral=True,
        )

    @has_role_or_above()
    @discord.slash_command(name="voters", description="Show list of players who voted")
    async def voters_command(self, ctx):
        await ctx.defer(ephemeral=True)
        await ctx.followup.send(
            "Voting participant listing moved to backend. Use backend API `/voting/{context_type}/{context_id}/voters`.",
            ephemeral=True,
        )


def setup(bot):
    bot.add_cog(Voting(bot))
