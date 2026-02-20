"""
Parsing utilities extracted from bot/cogs/utility.py.

Contains event parsing, roster parsing, template extraction,
HTML formatting, and order/scoring helpers.
"""

import re
from collections import defaultdict
from datetime import datetime
from typing import Any

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands


# ── Discord helpers ────────────────────────────────────────


def has_role_or_above(required_role_name: str = "Enlistor"):
    """Check if a user has the required role or above it."""

    async def predicate(ctx, role_name=required_role_name):
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            return False
        if ctx.author.top_role.position >= role.position:
            return True
        await ctx.respond(
            "You do not have the required role to use this command.",
            ephemeral=True,
        )
        return False

    return commands.check(lambda ctx: predicate(ctx, required_role_name))


# ── Event parsing ──────────────────────────────────────────


def parse_event_line(event_text: str) -> dict[str, Any] | None:
    """
    Parse a single event description from IRC/group chat.
    Handles Discord markdown (**text**) and filters out player chat.

    Returns dict with keys: actor, target, action_type, details, raw_text, is_system_action
    """
    event_text = event_text.strip()
    if not event_text:
        return None

    event_text = re.sub(r"\*\*(.+?)\*\*", r"\1", event_text).strip()

    if event_text.startswith("(GROUP-DISCORD)"):
        return None

    # Filter player chat
    chat_pattern = re.match(r"^[A-Za-z0-9_\-|/*#]+\s*:\s+(.+)", event_text)
    if chat_pattern:
        message_after = chat_pattern.group(1)
        event_keywords = [
            "joined", "left", "deposited", "withdrew", "promoted", "demoted",
            "kicked", "rewarded", "invited", "Denied", "Accepted", "application",
            "group bank", "for reason",
        ]
        if not any(kw in event_text for kw in event_keywords):
            return None
        if re.match(r"^[A-Za-z0-9_\-|/*]+\s*[\(\|]", message_after):
            return None

    result = {
        "actor": None, "target": None, "action_type": "unknown",
        "details": {}, "raw_text": event_text, "is_system_action": False,
    }

    def extract_player(text_segment):
        m = re.search(r"([^\(]+?)\s*\(([^)]+)\)", text_segment)
        if m:
            return {"nickname": m.group(1).strip(), "account_name": m.group(2).strip()}
        return None

    def extract_name_only(text_segment):
        return {"nickname": text_segment.strip().rstrip("."), "account_name": None}

    # Join with invitation
    if " joined the group. Invited by " in event_text:
        parts = event_text.split(" joined the group. Invited by ")
        if len(parts) == 2:
            result["target"] = extract_player(parts[0])
            result["actor"] = extract_player(parts[1])
            result["action_type"] = "join"

    elif " has joined the group" in event_text:
        m = re.match(r"(.+?) has joined the group", event_text)
        if m:
            result["target"] = extract_player(m.group(1))
            result["action_type"] = "join"
            result["is_system_action"] = True

    elif " left the group as " in event_text:
        m = re.match(r"(.+?) left the group as (.+)", event_text)
        if m:
            result["target"] = extract_player(m.group(1))
            result["action_type"] = "leave"
            result["details"]["rank"] = m.group(2).strip()

    elif " left the group" in event_text or " has left the group" in event_text:
        m = re.match(r"(.+?) (?:has )?left the group", event_text)
        if m:
            result["target"] = extract_player(m.group(1))
            result["action_type"] = "leave"

    elif " is promoting " in event_text:
        m = re.match(r"(.+?) is promoting (.+?) from (.+?) to (.+?) \((.+?)\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_player(m.group(2))
            result["action_type"] = "promotion"
            result["details"] = {"from_rank": m.group(3).strip(), "to_rank": m.group(4).strip(), "reason": m.group(5).strip()}

    elif " is demoting " in event_text:
        m = re.match(r"(.+?) is demoting (.+?) from (.+?) to (.+?) \((.+?)\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_player(m.group(2))
            result["action_type"] = "demotion"
            result["details"] = {"from_rank": m.group(3).strip(), "to_rank": m.group(4).strip(), "reason": m.group(5).strip()}

    elif " has kicked " in event_text:
        m = re.match(r"(.+?) has kicked (.+?) as (.+?) \((.+?)\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_player(m.group(2))
            result["action_type"] = "kick"
            result["details"] = {"rank": m.group(3).strip(), "reason": m.group(4).strip()}

    elif " kicked " in event_text:
        m = re.match(r"(.+?) kicked (.+?) \((.+?)\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_player(m.group(2))
            result["action_type"] = "kick"
            result["details"]["reason"] = m.group(3).strip()

    elif " has rewarded account " in event_text:
        m = re.match(r"(.+?) has rewarded account (.+?) with \$([0-9,]+): (.+)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = {"nickname": None, "account_name": m.group(2).strip()}
            result["action_type"] = "money_reward"
            result["details"] = {"amount": m.group(3).replace(",", ""), "reason": m.group(4).strip()}

    elif " deposited $" in event_text and "bank" in event_text:
        m = re.match(r"(.+?) deposited \$([0-9,]+) in the group bank for (.+)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["action_type"] = "bank_deposit"
            result["details"] = {"amount": m.group(2).replace(",", ""), "reason": m.group(3).strip()}

    elif " deposited to " in event_text and "bank" in event_text:
        m = re.match(r"\$([0-9,]+) deposited to .+ bank \((.+)\)", event_text)
        if m:
            result["action_type"] = "bank_deposit"
            result["is_system_action"] = True
            result["details"] = {"amount": m.group(1).replace(",", ""), "reason": m.group(2).strip()}

    elif " withdrew " in event_text and "bank" in event_text and "for reason:" in event_text:
        m = re.match(r"(.+?) withdrew \$([0-9,]+) from .+ bank for reason:\s*(.+)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["action_type"] = "bank_withdraw"
            result["details"] = {"amount": m.group(2).replace(",", ""), "reason": m.group(3).strip()}

    elif " withdrew " in event_text and "bank" in event_text:
        m = re.match(r"(.+?) withdrew \$([0-9,]+) from .+ bank \((.+)\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["action_type"] = "bank_withdraw"
            result["details"] = {"amount": m.group(2).replace(",", ""), "reason": m.group(3).strip()}

    elif " warned " in event_text:
        m = re.match(r"(.+?) warned (.+?) \((.+?)\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_player(m.group(2))
            result["action_type"] = "warn"
            result["details"]["reason"] = m.group(3).strip()

    elif " has warned " in event_text:
        m = re.match(r"(.+?) has warned (.+?) \((.+?)\) \(\+?([0-9]+)%\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_player(m.group(2))
            result["action_type"] = "warn"
            result["details"] = {"reason": m.group(3).strip(), "warning_increase": m.group(4).strip()}

    elif "Top score deposit" in event_text or "Top Law Group" in event_text:
        m = re.match(r"\$([0-9,]+) deposited to .+ bank \((.+)\)", event_text)
        if m:
            result["action_type"] = "top_score_deposit"
            result["is_system_action"] = True
            result["details"] = {"amount": m.group(1).replace(",", ""), "source": m.group(2).strip()}

    elif " has invited " in event_text:
        m = re.match(r"(.+?) has invited (.+?)\.?$", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_name_only(m.group(2))
            result["action_type"] = "invite"

    elif " has Denied " in event_text or " has denied " in event_text:
        m = re.match(r"(.+?) has [Dd]enied (.+?)'s application\.? \((.+?)\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_name_only(m.group(2))
            result["action_type"] = "application_deny"
            result["details"]["reason"] = m.group(3).strip()

    elif " has Accepted " in event_text or " has accepted " in event_text:
        m = re.match(r"(.+?) has [Aa]ccepted (.+?)'s application\.? \((.+?)\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_name_only(m.group(2))
            result["action_type"] = "application_accept"
            result["details"]["reason"] = m.group(3).strip()

    elif " has submitted an application" in event_text:
        m = re.match(r"(.+?) has submitted an application", event_text)
        if m:
            result["target"] = extract_name_only(m.group(1))
            result["action_type"] = "application_submit"
            result["is_system_action"] = True

    elif " has deleted " in event_text and "application" in event_text:
        m = re.match(r"(.+?) has deleted (.+?)'s application\.? \((.+?)\)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["target"] = extract_name_only(m.group(2))
            result["action_type"] = "application_delete"
            result["details"]["reason"] = m.group(3).strip()

    elif " created " in event_text:
        m = re.match(r"(.+?) created (.+)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["action_type"] = "create_group"
            result["details"]["group_name"] = m.group(2).strip()

    elif " updated the group info" in event_text:
        m = re.match(r"(.+?) updated the group info", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["action_type"] = "update_group_info"

    elif "rewarded all online members" in event_text:
        m = re.match(r"(.+?) has rewarded all online members with \$([0-9,]+) each: (.+)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["action_type"] = "mass_reward"
            result["details"] = {"amount": m.group(2).replace(",", ""), "reason": m.group(3).strip()}

    elif "has promoted group:" in event_text:
        m = re.match(r"(.+?) has promoted group: (.+?) to level: ([0-9]+)", event_text)
        if m:
            result["actor"] = extract_player(m.group(1))
            result["action_type"] = "group_promotion"
            result["details"] = {"group_name": m.group(2).strip(), "level": m.group(3).strip()}

    elif "has successfully taken over" in event_text:
        m = re.match(r"(.+?) has successfully taken over all of (.+)", event_text)
        if m:
            result["action_type"] = "territory_takeover"
            result["is_system_action"] = True
            result["details"] = {"group_name": m.group(1).strip(), "territory": m.group(2).strip()}

    return result


# ── HTML formatting ────────────────────────────────────────


def format_html_content(html_content: str) -> str:
    """Convert HTML to plain text preserving paragraph breaks."""
    if not html_content:
        return ""

    html_content = re.sub(r"<br\s*/?>", "\n", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"</p>", "\n\n", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"</div>", "\n\n", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"<p[^>]*>", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"<div[^>]*>", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"<[^>]+>", "", html_content)

    for entity, char in [
        ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
        ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"),
    ]:
        html_content = html_content.replace(entity, char)

    html_content = re.sub(r" +", " ", html_content)
    lines = [line.strip() for line in html_content.split("\n")]
    html_content = "\n".join(lines)
    html_content = re.sub(r"\n{3,}", "\n\n", html_content)
    return html_content.strip()


# ── Roster parsing ─────────────────────────────────────────


def parse_roster(file_path: str) -> list[dict[str, Any]]:
    """Parse roster.txt with member info."""
    members = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split()
                    if len(parts) < 6:
                        continue

                    nickname, account_name, rank = parts[0], parts[1], parts[2]

                    warning_idx = None
                    for i, part in enumerate(parts):
                        if part.endswith("%"):
                            warning_idx = i
                            break
                    if warning_idx is None:
                        continue

                    warning_level = parts[warning_idx].rstrip("%")
                    last_rank_change = " ".join(parts[warning_idx + 1:])

                    last_online_parts = []
                    has_afk = False
                    afk_time = None
                    idx = 3
                    while idx < warning_idx:
                        if parts[idx] == "AFK":
                            has_afk = True
                            if idx + 1 < warning_idx:
                                afk_time = parts[idx + 1]
                                idx += 2
                                continue
                        last_online_parts.append(parts[idx])
                        idx += 1

                    members.append({
                        "nickname": nickname,
                        "account_name": account_name,
                        "rank": rank,
                        "last_online": " ".join(last_online_parts),
                        "afk_status": has_afk,
                        "afk_time": afk_time,
                        "warning_level": warning_level,
                        "last_rank_change": last_rank_change,
                    })
                except Exception:
                    continue
    except FileNotFoundError:
        return []
    return members


# ── Template extraction ────────────────────────────────────


def extract_template_info(template_text: str) -> dict[str, str | None]:
    """Extract nickname, account_name, mta_serial from application template."""
    result: dict[str, str | None] = {"nickname": None, "account_name": None, "mta_serial": None}

    m = re.search(
        r"In-game nickname\s*:?\s*\n?\s*:\s*(.+?)(?=\n\s*Account name|\n\s*Your MTA|\n\s*English|\n\n|$)",
        template_text, re.IGNORECASE | re.DOTALL,
    )
    if m:
        val = re.sub(r"[\n:]+$", "", m.group(1)).strip()
        if val:
            result["nickname"] = val

    m = re.search(
        r"Account name\s*:?\s*\n?\s*:\s*(.+?)(?=\n\s*Your MTA|\n\s*English|\n\s*Do you|\n\n|$)",
        template_text, re.IGNORECASE | re.DOTALL,
    )
    if m:
        val = re.sub(r"[\n:]+$", "", m.group(1)).strip()
        if val:
            result["account_name"] = val

    m = re.search(r"Your MTA serial\s*:?\s*\n?\s*:\s*([A-F0-9]+)", template_text, re.IGNORECASE)
    if m:
        result["mta_serial"] = m.group(1).strip()

    return result


# ── Order helpers ──────────────────────────────────────────


ORDERS_CATALOG = {
    "1": {"description": "APB Jailed", "payout": "$1,500,000"},
    "2": {"description": "7.5K Arrest Points", "payout": "$1,000,000"},
    "3": {"description": "15K Arrest Points", "payout": "$2,000,000"},
    "4": {"description": "30K Arrest Points", "payout": "$4,000,000"},
    "5": {"description": "50K Arrest Points", "payout": "$8,000,000"},
    "6": {"description": "50 Stores Robbed", "payout": "$1,500,000"},
    "7": {"description": "50K Reputation Points", "payout": "$1,500,000"},
    "8": {"description": "100K Reputation Points", "payout": "$3,000,000"},
    "9": {"description": "150K Reputation Points", "payout": "$5,000,000"},
    "10": {"description": "200K Reputation Points", "payout": "$8,000,000"},
}


def get_order_details(order_number: str) -> dict[str, str] | None:
    m = re.search(r"#?(\d+)", order_number)
    if not m:
        return None
    return ORDERS_CATALOG.get(m.group(1))


def extract_user_orders_data(text: str, raw_html: str | None = None) -> list[dict[str, Any]]:
    """Extract user order submissions from text."""
    results = []
    pattern = (
        r"Ingame name\s*:\s*(.+?)\s*Account name\s*:\s*(.+?)\s*"
        r"Completed Orders\s*:\s*(.+?)\s*"
        r"Proof(?:\s*\(Required parts explained in rules\s*)?:\s*(.+?)"
        r"(?=Ingame name\s*:|$)"
    )

    for m in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
        nickname = " ".join(m.group(1).split())
        account_name = " ".join(m.group(2).split())
        completed_orders = " ".join(m.group(3).split())
        proof = " ".join(m.group(4).split())

        if not nickname or len(nickname) < 2 or not account_name or len(account_name) < 2:
            return []

        order_details = get_order_details(completed_orders)
        if not order_details:
            return []

        proof_url = None
        if raw_html:
            link_m = re.search(
                r"Proof[^:]*:\s*<a[^>]+href=[\"']([^\"']+)[\"']", raw_html, re.IGNORECASE | re.DOTALL,
            )
            if link_m:
                proof_url = link_m.group(1)

        if not proof_url:
            url_m = re.search(r"(https?://[^\s]+)", proof)
            if url_m:
                proof_url = url_m.group(1)

        if not proof_url:
            return []

        results.append({
            "nickname": nickname,
            "account_name": account_name,
            "completed_orders": completed_orders,
            "order_description": order_details["description"],
            "payout": order_details["payout"],
            "proof": proof,
            "proof_url": proof_url,
        })

    return results


# ── Image URL extraction ───────────────────────────────────


async def extract_direct_image_url(url: str) -> str | None:
    """Extract direct image URL from image hosting services."""
    if not url:
        return None

    if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]):
        return url

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                for prop in ["og:image", "twitter:image"]:
                    tag = soup.find("meta", property=prop)
                    if tag and tag.get("content"):
                        content = tag["content"]
                        if content.startswith("//"):
                            content = "https:" + content
                        return content
    except Exception:
        return None

    return None
