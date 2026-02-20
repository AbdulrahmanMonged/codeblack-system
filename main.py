from bot import create_bot
from bot.config import get_settings

settings = get_settings()

cogs = [
    "Events",
    "Tasks",
    "Management",
    "Voting",
    "GroupChatWatcher",
    "PlayerMangment",
    "IRCReader",
    "Administration",
    "ActivityMonitor",
    "ActivityCommands",
    "ColorCommands",
]

bot = create_bot()

for cog in cogs:
    bot.load_extension(f"bot.cogs.{cog}")

bot.run(settings.DISCORD_BOT_TOKEN)
