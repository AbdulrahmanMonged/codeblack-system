import logging
from enum import Enum

import discord
from discord.ext import commands
from discord.ui import Modal, InputText

from bot.core.redis import RedisManager
from bot.utils.parsers import extract_template_info, has_role_or_above
from .Voting import VotingView

logger = logging.getLogger(__name__)

RECRUITMENT_TOPIC_ID = "407654"


class Decisions(Enum):
    ACCEPTED = "accepted"
    DECLINED = "declined"
    PENDING = "pending"


class DeclinedModal(Modal):
    def __init__(self, cog, ctx, nickname: str, account_name: str):
        super().__init__(title=f"Decline Application For {nickname} ({account_name})")
        self.cog = cog
        self.ctx = ctx
        self.nickname = nickname
        self.account_name = account_name

        self.add_item(
            InputText(
                label="Reason(s) for declining",
                placeholder="Enter reasons separated by lines...",
                style=discord.InputTextStyle.long,
                required=True,
                max_length=1000,
            )
        )

        self.add_item(
            InputText(
                label="Reapplication Date",
                placeholder="e.g., 2025-12-31 or December 31, 2025",
                style=discord.InputTextStyle.short,
                required=True,
                max_length=100,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        reasons = self.children[0].value
        date = self.children[1].value

        await interaction.response.defer()

        thread = self.ctx.channel
        starter_msg = await thread.fetch_message(thread.id)
        content = starter_msg.content
        author = self.ctx.author
        role = author.roles[-1]
        extracted_info = extract_template_info(content)

        msg = self.cog._create_message(
            extracted_info["nickname"],
            extracted_info["account_name"],
            role,
            author.nick if author.nick else author.display_name,
            Decisions.DECLINED,
            reasons=reasons,
            application=content,
            date=date,
        )

        if msg:
            voting_controls_disabled = await self.cog._disable_voting_view(thread)

            voting_cog = self.cog.bot.get_cog("Voting")
            if voting_cog:
                await voting_cog.end_voting_and_update_message(thread.id)

            if voting_controls_disabled:
                await thread.send(
                    "Voting controls are disabled. Final tally is available in the backend dashboard."
                )

            forum_service = self.cog.bot.forum_service
            redis_key = f"REDACTED:forum:thread:{thread.id}:forum:{RECRUITMENT_TOPIC_ID}"
            existing_msg_id = await RedisManager.get(redis_key)

            if existing_msg_id:
                success = await forum_service.modify_post(
                    msg, thread_id=str(thread.id), topic_number=RECRUITMENT_TOPIC_ID
                )
                if success:
                    await interaction.followup.send("Application declined and forum post modified successfully!")
                else:
                    await interaction.followup.send("Application declined but failed to modify forum post!")
            else:
                success = await forum_service.send_message(
                    RECRUITMENT_TOPIC_ID, msg, thread_id=str(thread.id)
                )
                if success:
                    await interaction.followup.send("Application declined and forum post created successfully!")
                else:
                    await interaction.followup.send("Application declined but failed to create forum post!")


class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _disable_voting_view(self, thread: discord.Thread) -> bool:
        """Find and disable any legacy voting view in the thread."""
        try:
            async for message in thread.history(limit=50):
                if message.author.id == self.bot.user.id and message.components:
                    for component in message.components:
                        if hasattr(component, "children"):
                            for child in component.children:
                                if hasattr(child, "custom_id") and child.custom_id in [
                                    "vote_yes",
                                    "vote_no",
                                ]:
                                    view = VotingView(thread.id)
                                    view.disable_all_items()
                                    await message.edit(view=view)
                                    return True
        except Exception as e:
            logger.error(f"Error disabling voting view: {e}")
        return False

    async def _decision_taker_function(self, ctx, decision: Decisions, reasons=None, date=None):
        await ctx.defer()
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.followup.send("Must be used in a forum post!", ephemeral=True)
            return

        if not isinstance(ctx.channel.parent, discord.ForumChannel):
            await ctx.followup.send("Must be used in a forum, not a regular thread!", ephemeral=True)
            return

        thread = ctx.channel
        starter_msg = await thread.fetch_message(thread.id)
        content = starter_msg.content
        author = ctx.author
        role = author.roles[-1]
        extracted_info = extract_template_info(content)

        if not extracted_info["account_name"]:
            await ctx.followup.send("Account name not found!")
            return
        if not extracted_info["nickname"]:
            await ctx.followup.send("Nickname not found!")
            return

        msg = self._create_message(
            extracted_info["nickname"],
            extracted_info["account_name"],
            role,
            author.nick if author.nick else author.display_name,
            decision,
            reasons=reasons,
            application=content,
            date=date,
        )

        if not msg:
            return msg

        forum_service = self.bot.forum_service

        if decision == Decisions.PENDING:
            success = await forum_service.send_message(RECRUITMENT_TOPIC_ID, msg)
            if success:
                await ctx.followup.send("Set as pending and posted to forum successfully!")
            else:
                await ctx.followup.send("Set as pending but failed to post to forum!")
            return msg

        # For ACCEPTED or DECLINED, disable legacy voting controls
        voting_controls_disabled = await self._disable_voting_view(thread)

        voting_cog = self.bot.get_cog("Voting")
        if voting_cog:
            await voting_cog.end_voting_and_update_message(thread.id)

        if voting_controls_disabled:
            await thread.send(
                "Voting controls are disabled. Final tally is available in the backend dashboard."
            )

        redis_key = f"REDACTED:forum:thread:{thread.id}:forum:{RECRUITMENT_TOPIC_ID}"
        existing_msg_id = await RedisManager.get(redis_key)

        if existing_msg_id:
            success = await forum_service.modify_post(
                msg, thread_id=str(thread.id), topic_number=RECRUITMENT_TOPIC_ID
            )
            if success:
                await ctx.followup.send("Decision updated and forum post modified successfully!")
            else:
                await ctx.followup.send("Decision updated but failed to modify forum post!")
        else:
            success = await forum_service.send_message(
                RECRUITMENT_TOPIC_ID, msg, thread_id=str(thread.id)
            )
            if success:
                await ctx.followup.send("Decision set and forum post created successfully!")
            else:
                await ctx.followup.send("Decision set but failed to create forum post!")

        return msg

    def _create_message(
        self, nickname, accName, rank, author, decision: Decisions,
        reasons=None, date=None, application=None,
    ):
        match decision:
            case Decisions.ACCEPTED:
                return f"""[img]https://i.ibb.co/zh9m4jf/REDACTED-application-result.png[/img]

[font=trebuchet ms][b][size=12pt]{nickname} | {accName}[/size][/b][/font]

[hr]

Your application to become a REDACTED delegate has been [b][color=green]accepted[/color][/b].
As a final step to join the group, you must conduct an interview with any Sentinel+ that is available. You can contact them in-game or through our [url=https://discord.gg/qscUeckMmJ]discord server[/url]. If after 48 hours no contact for an interview has been made, we will consider that you are no longer interested in joining the group.

Thank you for your interest,
{rank}, {author}"""

            case Decisions.PENDING:
                return f"""[img]https://i.ibb.co/zh9m4jf/REDACTED-application-result.png[/img]

[font=trebuchet ms][b][size=12pt]{nickname} | {accName}[/size][/b][/font]

[spoiler]{application}[/spoiler]

[hr]

Your application to become a REDACTED delegate is now set as [b][color=orange]pending[/color][/b]. The voting process has begun, and a response will be given in no less than 72 hours.
If after 72 hours you have not received a response to your application, you are authorized to contact a Sentinel+ for review.

Thank you for your interest,
{rank}, {author}"""

            case Decisions.DECLINED:
                return f"""[img]https://i.ibb.co/zh9m4jf/REDACTED-application-result.png[/img]

[font=trebuchet ms][b][size=12pt]{nickname} | {accName}[/size][/b][/font]

[hr]

Your application to become a REDACTED delegate has been [b][color=red]rejected[/color][/b].
This is because most of the leaders have voted negative on your application, mainly for the following reason:
- {"\n- ".join(reason for reason in reasons.split("\n"))}

You can send a new application after {date}.
Thank you for your interest,
{rank}, {author}"""

    @has_role_or_above()
    @discord.slash_command(name="set_pending", description="Setting an application as pending")
    async def set_pending(self, ctx):
        await self._decision_taker_function(ctx, Decisions.PENDING)

    @has_role_or_above()
    @discord.slash_command(name="set_declined", description="Setting an application as declined")
    async def set_declined(self, ctx):
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.respond("Must be used in a forum post!", ephemeral=True)
            return

        if not isinstance(ctx.channel.parent, discord.ForumChannel):
            await ctx.respond("Must be used in a forum, not a regular thread!", ephemeral=True)
            return

        thread = ctx.channel
        try:
            starter_msg = await thread.fetch_message(thread.id)
        except Exception:
            await ctx.respond("Failed to fetch the starter message!", ephemeral=True)
            return

        content = starter_msg.content
        extracted_info = extract_template_info(content)

        if not extracted_info["account_name"]:
            await ctx.respond("Account name not found in the application!", ephemeral=True)
            return
        if not extracted_info["nickname"]:
            await ctx.respond("Nickname not found in the application!", ephemeral=True)
            return

        modal = DeclinedModal(self, ctx, extracted_info["nickname"], extracted_info["account_name"])
        await ctx.send_modal(modal)

    @has_role_or_above()
    @discord.slash_command(name="set_approved", description="Setting an application as approved")
    async def set_approved(self, ctx):
        await self._decision_taker_function(ctx, Decisions.ACCEPTED)


def setup(bot):
    bot.add_cog(Management(bot))
