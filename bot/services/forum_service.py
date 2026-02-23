"""
Forum interaction service - posting, editing, watching topics on cit.gg.
"""

import logging
import re

from bs4 import BeautifulSoup

from bot.cloudflare.http_client import HttpClient
from bot.core.redis import RedisManager

logger = logging.getLogger(__name__)

BOARD_NUMBER = "1537"
REDIS_WATCH_PREFIX = "REDACTED:forum:watch"
REDIS_THREAD_PREFIX = "REDACTED:forum:thread"


class ForumService:

    def __init__(self, http_client: HttpClient, redis: type[RedisManager]):
        self._http = http_client
        self._redis = redis

    async def send_message(
        self,
        topic_number: str,
        message_text: str,
        board_number: str | None = None,
        thread_id: str | None = None,
    ) -> bool:
        """Post a message to a forum topic."""
        if board_number is None:
            board_number = BOARD_NUMBER

        # Step 1: Get reply page for CSRF tokens
        reply_url = f"https://cit.gg/index.php?action=post;topic={topic_number}.0"
        response = await self._http.get(reply_url)

        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch reply page: {response}")
            return False

        text = response.text
        tokens = self._extract_tokens(text)
        if not tokens:
            return False

        # Extract subject from page title
        soup = BeautifulSoup(text, "html.parser")
        title_tag = soup.find("title")
        if title_tag and " - " in title_tag.get_text(strip=True):
            subject = f"Re: {title_tag.get_text(strip=True).split(' - ')[0].strip()}"
        else:
            subject = "Re: Topic"

        # Step 2: Post message
        post_url = (
            f"https://cit.gg/index.php?action=post2;start=0;board={board_number}"
        )
        data = {
            "topic": topic_number,
            "subject": subject,
            "icon": "xx",
            "message": message_text,
            "message_mode": "0",
            "notify": "0",
            "goback": "1",
            "last_msg": tokens["last_msg"],
            "additional_options": "0",
            tokens["csrf_name"]: tokens["csrf_value"],
            "seqnum": tokens["seqnum"],
        }

        response = await self._http.post(post_url, data=data)
        if not response:
            logger.error("Failed to post message")
            return False

        if response.status_code in (200, 302, 303):
            logger.info(f"Message posted to topic {topic_number}")

            # Save forum msg ID to Redis
            if thread_id:
                msg_match = re.search(r"msg=(\d+)", response.text)
                if msg_match:
                    key = f"{REDIS_THREAD_PREFIX}:{thread_id}:forum:{topic_number}"
                    await self._redis.set(key, msg_match.group(1), expire=604800)

            return True

        logger.error(f"Post failed: {response.status_code}")
        return False

    async def modify_post(
        self,
        message_text: str,
        thread_id: str,
        topic_number: str,
        board_number: str | None = None,
        msg_id: str | None = None,
    ) -> bool:
        """Edit an existing forum post."""
        if board_number is None:
            board_number = BOARD_NUMBER

        if not msg_id:
            key = f"{REDIS_THREAD_PREFIX}:{thread_id}:forum:{topic_number}"
            msg_id = await self._redis.get(key)
            if not msg_id:
                logger.error(f"No message ID for thread {thread_id}")
                return False

        # Get edit page for tokens
        edit_url = (
            f"https://cit.gg/index.php?action=post;msg={msg_id};topic={topic_number}.new"
        )
        response = await self._http.get(edit_url)

        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch edit page")
            return False

        tokens = self._extract_tokens(response.text)
        if not tokens:
            return False

        subject_match = re.search(
            r'<input[^>]*name="subject"[^>]*value="([^"]*)"', response.text
        )
        subject = subject_match.group(1) if subject_match else f"Re: Topic {topic_number}"

        # Submit edit
        post_url = (
            f"https://cit.gg/index.php?action=post2;start=15;msg={msg_id};"
            f"{tokens['csrf_name']}={tokens['csrf_value']};board={board_number}"
        )
        data = {
            "topic": topic_number,
            "subject": subject,
            "icon": "xx",
            "message": message_text,
            "message_mode": "0",
            "goback": "1",
            "last_msg": tokens.get("last_msg", msg_id),
            "additional_options": "0",
            tokens["csrf_name"]: tokens["csrf_value"],
            "seqnum": tokens["seqnum"],
        }

        response = await self._http.post(post_url, data=data)
        if response and response.status_code == 200:
            logger.info(f"Post {msg_id} modified")
            return True

        logger.error(f"Modify failed: {response.status_code if response else 'None'}")
        return False

    async def get_last_message(self, topic_number: str) -> dict | None:
        """Fetch the last message from a topic."""
        url = f"https://cit.gg/index.php?topic={topic_number}.new"
        response = await self._http.get(url)

        if not response or response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        message_divs = soup.find_all(
            "div", {"class": "inner", "id": re.compile(r"^msg_\d+$")}
        )

        if not message_divs:
            message_divs = soup.find_all("div", id=re.compile(r"^msg_\d+$"))

        if not message_divs:
            return None

        last = message_divs[-1]
        msg_id = last.get("id", "").replace("msg_", "")

        # Extract attachments
        attachments = self._extract_attachments(last)

        return {
            "content": str(last),
            "msg_number": msg_id,
            "has_attachments": len(attachments) > 0,
            "attachments": attachments,
        }

    async def watch_for_new_posts(self, topic_number: str) -> dict | bool | None:
        """
        Check if there are new posts in a topic.

        Returns:
            - dict with message data if new post found
            - False if no new posts
            - None on error
        """
        message_data = await self.get_last_message(topic_number)
        if not message_data:
            return None

        current_msg = message_data.get("msg_number")
        if not current_msg:
            return None

        redis_key = f"{REDIS_WATCH_PREFIX}:{topic_number}:last_msg"
        stored_msg = await self._redis.get(redis_key)

        if stored_msg:
            if stored_msg == current_msg:
                return False
            else:
                await self._redis.set(redis_key, current_msg, expire=604800)
                message_data["is_new"] = True
                return message_data
        else:
            await self._redis.set(redis_key, current_msg, expire=604800)
            message_data["is_new"] = True
            return message_data

    # ── Private helpers ────────────────────────────────────

    def _extract_tokens(self, html: str) -> dict | None:
        csrf_match = re.search(r'name="([a-f0-9]+)" value="([a-f0-9]+)"', html)
        seqnum_match = re.search(r'name="seqnum" value="(\d+)"', html)
        last_msg_match = re.search(r'last_msg=(\d+)', html)

        if not csrf_match or not seqnum_match:
            logger.error("Failed to extract CSRF tokens")
            return None

        return {
            "csrf_name": csrf_match.group(1),
            "csrf_value": csrf_match.group(2),
            "seqnum": seqnum_match.group(1),
            "last_msg": last_msg_match.group(1) if last_msg_match else "0",
        }

    def _extract_attachments(self, div) -> dict:
        attachments = {}
        counters = {"img": 0, "file": 0, "link": 0}

        for img in div.find_all("img"):
            counters["img"] += 1
            attachments[f"img{counters['img']}"] = {
                "type": "image",
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
            }

        for link in div.find_all(
            "a", href=re.compile(r"(attachment|download|dlattach)")
        ):
            counters["file"] += 1
            attachments[f"file{counters['file']}"] = {
                "type": "file",
                "url": link.get("href", ""),
                "text": link.get_text(strip=True),
            }

        for link in div.find_all("a", href=re.compile(r"^https?://")):
            href = link.get("href", "")
            if not any(x in href for x in ("attachment", "download", "dlattach")):
                counters["link"] += 1
                attachments[f"link{counters['link']}"] = {
                    "type": "link",
                    "url": href,
                    "text": link.get_text(strip=True),
                }

        return attachments
