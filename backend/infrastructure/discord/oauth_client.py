from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx


class DiscordOAuthError(RuntimeError):
    pass


class DiscordOAuthClient:
    def __init__(
        self,
        *,
        api_base_url: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        oauth_scopes: str,
        bot_token: str,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.oauth_scopes = oauth_scopes
        self.bot_token = bot_token

    def build_authorize_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.oauth_scopes,
            "state": state,
            "prompt": "consent",
        }
        return f"{self.api_base_url}/oauth2/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.api_base_url}/oauth2/token",
                data=payload,
                headers=headers,
            )
        if response.status_code >= 400:
            raise DiscordOAuthError(
                f"Discord token exchange failed ({response.status_code}): {response.text}"
            )
        data = response.json()
        if "access_token" not in data:
            raise DiscordOAuthError("Discord token exchange returned no access_token")
        return data

    async def fetch_user(self, access_token: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.api_base_url}/users/@me",
                headers=headers,
            )
        if response.status_code >= 400:
            raise DiscordOAuthError(
                f"Discord /users/@me failed ({response.status_code}): {response.text}"
            )
        return response.json()

    async def fetch_user_guilds(self, access_token: str) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.api_base_url}/users/@me/guilds",
                headers=headers,
            )
        if response.status_code >= 400:
            raise DiscordOAuthError(
                f"Discord /users/@me/guilds failed ({response.status_code}): {response.text}"
            )
        payload = response.json()
        if not isinstance(payload, list):
            raise DiscordOAuthError("Discord /users/@me/guilds response was not a list")
        return payload

    async def fetch_guild_roles(self, guild_id: int) -> list[dict[str, Any]]:
        if not self.bot_token:
            raise DiscordOAuthError("DISCORD_BOT_TOKEN is required to fetch guild roles")
        headers = {"Authorization": f"Bot {self.bot_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.api_base_url}/guilds/{guild_id}/roles",
                headers=headers,
            )
        if response.status_code >= 400:
            raise DiscordOAuthError(
                f"Discord guild roles failed ({response.status_code}): {response.text}"
            )
        payload = response.json()
        if not isinstance(payload, list):
            raise DiscordOAuthError("Discord guild roles response was not a list")
        return payload

    async def fetch_guild_member(self, guild_id: int, discord_user_id: int) -> dict[str, Any]:
        if not self.bot_token:
            raise DiscordOAuthError("DISCORD_BOT_TOKEN is required to fetch guild member")
        headers = {"Authorization": f"Bot {self.bot_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.api_base_url}/guilds/{guild_id}/members/{discord_user_id}",
                headers=headers,
            )
        if response.status_code == 404:
            raise DiscordOAuthError("User is not a guild member")
        if response.status_code >= 400:
            raise DiscordOAuthError(
                f"Discord guild member failed ({response.status_code}): {response.text}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise DiscordOAuthError("Discord guild member response was not an object")
        return payload
