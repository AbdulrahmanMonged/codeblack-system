import asyncio
import logging
from datetime import datetime

import discord
from discord.ext import commands

from bot.utils.parsers import parse_event_line

logger = logging.getLogger(__name__)


class GroupChatWatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gc_channel_id = 1434431786368241725
        self.event_queue = asyncio.Queue()
        self.queue_processor_task = None
        self._processor_started = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._processor_started:
            self.queue_processor_task = asyncio.create_task(self._process_event_queue())
            self._processor_started = True
            logger.info("GroupChatWatcher: Event queue processor started")

    def cog_unload(self):
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            logger.info("GroupChatWatcher: Event queue processor stopped")

    async def _process_event_queue(self):
        """Background task to process events from the queue."""
        while True:
            try:
                event_data = await self.event_queue.get()
                try:
                    await self._insert_event(event_data)
                    logger.debug(f"Event inserted: {event_data['action_type']}")
                except Exception as e:
                    logger.error(f"Error inserting event: {e}")
                finally:
                    self.event_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(1)

    async def _insert_event(self, event_data: dict):
        """Insert a parsed event using the service layer."""
        event_service = self.bot.event_service
        player_service = self.bot.player_service

        actor = event_data.get("actor")
        target = event_data.get("target")
        action_type = event_data.get("action_type")
        details = event_data.get("details", {})
        raw_text = event_data.get("raw_text", "")
        is_system_action = event_data.get("is_system_action", False)

        timestamp = datetime.now()

        actor_nickname = actor.get("nickname") if actor else None
        actor_account_name = actor.get("account_name") if actor else None
        target_nickname = target.get("nickname") if target else None
        target_account_name = target.get("account_name") if target else None

        # Upsert actors/targets in player DB
        if actor_account_name:
            await player_service.get_or_create(
                actor_account_name, nickname=actor_nickname, is_in_group=True
            )

        if target_account_name:
            if action_type in ("join", "promotion", "demotion", "warn", "money_reward", "bank_deposit", "bank_withdraw"):
                initial_in_group = True
            elif action_type in ("leave", "kick"):
                initial_in_group = False
            else:
                initial_in_group = False

            await player_service.get_or_create(
                target_account_name, nickname=target_nickname, is_in_group=initial_in_group
            )

        # Update group membership status
        if target_account_name:
            if action_type == "join":
                await player_service.mark_joined_group(target_account_name)
            elif action_type in ("leave", "kick"):
                await player_service.mark_left_group(target_account_name)

        # Log the event
        await event_service.log_event(
            timestamp=timestamp,
            action_type=action_type,
            raw_text=raw_text,
            actor_nickname=actor_nickname,
            actor_account_name=actor_account_name,
            target_nickname=target_nickname,
            target_account_name=target_account_name,
            details=details,
            is_system_action=is_system_action,
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == self.gc_channel_id:
            if message.author.id == 403112358630916096:
                parsed_event = parse_event_line(message.content)
                if parsed_event and parsed_event.get("action_type") != "unknown":
                    await self.event_queue.put(parsed_event)
                    logger.debug(f"Event queued: {parsed_event['action_type']} (Queue size: {self.event_queue.qsize()})")


def setup(bot):
    bot.add_cog(GroupChatWatcher(bot))
