"""
Web scraping service for game data (scores, online players).
"""

import logging
import re

from bs4 import BeautifulSoup

from bot.cloudflare.http_client import HttpClient

logger = logging.getLogger(__name__)


class ScraperService:

    def __init__(self, http_client: HttpClient):
        self._http = http_client

    async def fetch_cop_live_scores(self) -> list[dict] | None:
        """Fetch COP live leaderboard scores."""
        url = "https://cit.gg/rpp/coplive.php"
        response = await self._http.get(url)

        if not response or response.status_code != 200:
            logger.error("Failed to fetch cop scores")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        if not table:
            return None

        scores = []
        for row in table.find_all("tr")[1:]:  # Skip header
            cells = row.find_all("td")
            if len(cells) >= 2:
                scores.append(
                    {
                        "group": cells[0].get_text(strip=True),
                        "arrest_points": cells[1].get_text(strip=True),
                    }
                )

        logger.info(f"Fetched {len(scores)} cop scores")
        return scores

    async def fetch_players_by_group(
        self,
        group_filter: str = "REDACTED",
        url: str = "https://cit.gg/rpp/players.php",
    ) -> list[dict] | None:
        """Fetch online players filtered by group."""
        response = await self._http.get(url)

        if not response or response.status_code != 200:
            logger.error("Failed to fetch player data")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="sortable")
        if not table:
            return None

        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

        if not rows:
            return None

        players = []
        group_lower = group_filter.lower()

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 10:
                continue

            group = cells[6].get_text(strip=True)
            if group.lower() != group_lower:
                continue

            player = {
                "name": cells[0].get_text(strip=True),
                "account_name": cells[1].get_text(strip=True),
                "occupation": cells[2].get_text(strip=True),
                "wl": cells[3].get_text(strip=True),
                "cash": cells[4].get_text(strip=True),
                "playtime": cells[5].get_text(strip=True),
                "group": group,
                "squad": cells[7].get_text(strip=True),
                "ping": cells[8].get_text(strip=True),
            }

            # RGB color
            style = cells[0].get("style", "")
            rgb_match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", style)
            if rgb_match:
                player["rgb_color"] = {
                    "r": int(rgb_match.group(1)),
                    "g": int(rgb_match.group(2)),
                    "b": int(rgb_match.group(3)),
                }

            # Country
            country_cell = cells[9]
            country_img = country_cell.find("img")
            if country_img:
                player["country"] = country_img.get(
                    "title", country_img.get("alt", "N/A")
                )
            else:
                player["country"] = country_cell.get_text(strip=True) or "N/A"

            players.append(player)

        logger.info(f"Found {len(players)} players in '{group_filter}'")
        return players
