import asyncio
import logging
import random
import re
import threading
from urllib.parse import urlparse

import discord
import irc.bot
import irc.connection
from discord.ext import commands

from bot.config import get_settings

try:
    import socks

    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Module-level singleton to persist IRC bot across cog reloads
_irc_bot_instance = None
_irc_thread = None


def parse_proxy_url(proxy_url: str) -> dict | None:
    """Parse proxy URL in format: protocol://username:password@host:port"""
    if not proxy_url:
        return None
    try:
        parsed = urlparse(proxy_url)
        return {
            "proxy_type": parsed.scheme,
            "proxy_addr": parsed.hostname,
            "proxy_port": parsed.port,
            "proxy_username": parsed.username,
            "proxy_password": parsed.password,
        }
    except Exception as e:
        logger.warning(f"Failed to parse proxy URL: {e}")
        return None


def filter_string(message: str) -> tuple[str, str]:
    """Clean IRC formatting and split sender:message."""
    clean_text = re.sub(r"[\x02\x03\x0f\x16\x1d\x1f]", "", message)
    clean_text = re.sub(r"\([^)]*\)", "", clean_text)
    clean_text = " ".join(clean_text.split())

    if ":" in clean_text:
        sender, msg = clean_text.split(":", 1)
        sender = sender.strip()
        msg = msg.strip()
    else:
        sender = ""
        msg = clean_text.strip()

    return sender, msg


class IRCBotClient(irc.bot.SingleServerIRCBot):
    """IRC bot that listens to messages and forwards them to Discord."""

    def __init__(
        self,
        channel: str,
        nickname: str,
        server: str,
        discord_bot,
        discord_channel_id: int,
        port: int = 6667,
        password: str | None = None,
        proxy_type=None,
        proxy_addr=None,
        proxy_port=None,
        proxy_username=None,
        proxy_password=None,
    ):
        logger.info(f"Initializing IRC bot: {nickname} on {server}:{port}")

        connect_factory = None
        if proxy_type and proxy_addr and proxy_port and SOCKS_AVAILABLE:
            logger.info(f"Configuring proxy: {proxy_type}://{proxy_addr}:{proxy_port}")

            proxy_type_map = {
                "socks4": socks.SOCKS4,
                "socks5": socks.SOCKS5,
                "http": socks.HTTP,
            }
            socks_type = proxy_type_map.get(proxy_type.lower(), socks.SOCKS5)

            def create_proxy_socket(sock):
                proxy_sock = socks.socksocket(sock.family, sock.type, sock.proto)
                proxy_sock.set_proxy(
                    proxy_type=socks_type,
                    addr=proxy_addr,
                    port=proxy_port,
                    username=proxy_username,
                    password=proxy_password,
                )
                return proxy_sock

            connect_factory = irc.connection.Factory(wrapper=create_proxy_socket)
        elif proxy_type and not SOCKS_AVAILABLE:
            logger.warning("Proxy requested but PySocks not available")

        if connect_factory:
            super().__init__(
                [(server, port)], nickname, nickname, connect_factory=connect_factory
            )
        else:
            super().__init__([(server, port)], nickname, nickname)

        self.connection.reconnection_interval = 60
        self.channel = channel
        self.password = password
        self.target_nickname = nickname
        self.nickname_recovered = False
        self.discord_bot = discord_bot
        self.discord_channel_id = discord_channel_id
        self.server_name = server
        self.server_port = port

    def on_welcome(self, connection, event):
        logger.info(f"IRC Connected with nick: {connection.get_nickname()}")

        if (
            connection.get_nickname() != self.target_nickname
            and self.password
            and not self.nickname_recovered
        ):
            logger.info(f"Attempting to recover nickname {self.target_nickname}...")
            connection.privmsg("NickServ", f"IDENTIFY {self.target_nickname} {self.password}")
            import time

            time.sleep(2)
            connection.privmsg("NickServ", f"GHOST {self.target_nickname}")
            time.sleep(1)
            connection.nick(self.target_nickname)
            self.nickname_recovered = True
        elif self.password:
            connection.privmsg("NickServ", f"IDENTIFY {self.password}")

        connection.join(self.channel)
        logger.info(f"Joining {self.channel}")

    def on_pubmsg(self, connection, event):
        message = event.arguments[0]
        actual_message = message[3:] if len(message) > 3 else message

        asyncio.run_coroutine_threadsafe(
            self._send_to_discord(actual_message), self.discord_bot.loop
        )

    async def _send_to_discord(self, message: str):
        try:
            channel = await self.discord_bot.fetch_channel(self.discord_channel_id)
            actual_sender, actual_message = filter_string(message)
            await channel.send(content=f"**{actual_sender}**: {actual_message}")
        except Exception as e:
            logger.error(f"Error sending to Discord: {e}")

    def on_privmsg(self, connection, event):
        sender = event.source.nick
        message = event.arguments[0]
        logger.debug(f"Private message from {sender}: {message}")

    def on_nicknameinuse(self, connection, event):
        alt_nick = f"{self.target_nickname}_{random.randint(100, 999)}"
        logger.warning(f"Nickname in use, trying alternative: {alt_nick}")
        connection.nick(alt_nick)

    def on_join(self, connection, event):
        joiner = event.source.nick
        channel = event.target
        if joiner == connection.get_nickname():
            logger.info(f"Successfully joined IRC channel: {channel}")

    def on_disconnect(self, connection, event):
        logger.warning("Disconnected from IRC server, will reconnect in 60s...")

    def get_version(self):
        return "CodeBlack IRC Bridge v2.0"

    def on_ping(self, connection, event):
        connection.pong(event.target)


class IRCReader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Start IRC bot when Discord bot is ready."""
        global _irc_bot_instance, _irc_thread

        if _irc_bot_instance is None:
            settings = get_settings()

            if not settings.IRC_NICKNAME:
                logger.warning("IRC_NICKNAME not set, skipping IRC bot startup")
                return

            proxy_url = settings.IRC_PROXY or settings.OXYLABS_PROXY
            proxy_config = parse_proxy_url(proxy_url)

            if proxy_config:
                logger.info(
                    f"Using proxy: {proxy_config['proxy_type']}://{proxy_config['proxy_addr']}:{proxy_config['proxy_port']}"
                )
            else:
                proxy_config = {
                    "proxy_type": None,
                    "proxy_addr": None,
                    "proxy_port": None,
                    "proxy_username": None,
                    "proxy_password": None,
                }
                logger.info("No proxy configured, connecting directly")

            _irc_bot_instance = IRCBotClient(
                channel=settings.IRC_CHANNEL,
                nickname=settings.IRC_NICKNAME,
                server=settings.IRC_SERVER,
                discord_bot=self.bot,
                discord_channel_id=settings.IRC_DISCORD_CHANNEL_ID,
                port=settings.IRC_PORT,
                password=settings.IRC_PASSWORD or None,
                **proxy_config,
            )

            _irc_thread = threading.Thread(target=_irc_bot_instance.start, daemon=True)
            _irc_thread.start()
            logger.info("IRC bot thread started")
        else:
            logger.info("IRC bot already running, updating Discord bot reference")
            _irc_bot_instance.discord_bot = self.bot

    def cog_unload(self):
        logger.info("IRCReader cog unloaded (IRC bot continues running)")


def setup(bot):
    bot.add_cog(IRCReader(bot))
