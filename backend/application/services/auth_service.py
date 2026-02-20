from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.application.dto.auth import AuthenticatedPrincipal, IssuedAccessToken
from backend.core.config import get_settings
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.core.security import (
    create_signed_token,
    decode_signed_token,
    random_jti,
)
from backend.infrastructure.discord.oauth_client import (
    DiscordOAuthClient,
    DiscordOAuthError,
)
from backend.infrastructure.repositories.auth_repository import AuthRepository


class AuthService:
    def __init__(self):
        self.settings = get_settings()

    def _oauth_client(self) -> DiscordOAuthClient:
        return DiscordOAuthClient(
            api_base_url=self.settings.DISCORD_API_BASE_URL,
            client_id=self.settings.DISCORD_CLIENT_ID,
            client_secret=self.settings.DISCORD_CLIENT_SECRET,
            redirect_uri=self.settings.DISCORD_REDIRECT_URI,
            oauth_scopes=self.settings.oauth_scopes,
            bot_token=self.settings.DISCORD_BOT_TOKEN,
        )

    def _ensure_oauth_config(self) -> None:
        if not self.settings.DISCORD_CLIENT_ID or not self.settings.DISCORD_CLIENT_SECRET:
            raise ApiException(
                status_code=500,
                error_code="OAUTH_CONFIG_MISSING",
                message="Discord OAuth credentials are not configured",
            )
        self._ensure_jwt_config()

    def _ensure_jwt_config(self) -> None:
        if not self.settings.JWT_SECRET:
            raise ApiException(
                status_code=500,
                error_code="JWT_SECRET_MISSING",
                message="JWT_SECRET is required for authentication",
            )

    async def build_discord_login(self, next_url: str | None = None) -> dict[str, Any]:
        self._ensure_oauth_config()
        state_token, expires_at = create_signed_token(
            settings=self.settings,
            token_type="oauth_state",
            claims={
                "nonce": random_jti(8),
                "next_url": next_url or "",
            },
            ttl_seconds=self.settings.BACKEND_AUTH_STATE_TTL_SECONDS,
        )
        authorize_url = self._oauth_client().build_authorize_url(state_token)
        return {
            "authorize_url": authorize_url,
            "state": state_token,
            "state_expires_at": expires_at,
            "next_url": next_url or "",
        }

    async def exchange_discord_callback(
        self,
        *,
        code: str,
        state: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[IssuedAccessToken, AuthenticatedPrincipal]:
        self._ensure_oauth_config()

        state_payload = decode_signed_token(
            settings=self.settings,
            token=state,
            expected_type="oauth_state",
        )
        _ = state_payload.get("nonce"), state_payload.get("next_url")

        client = self._oauth_client()
        try:
            token_payload = await client.exchange_code(code)
            user_payload = await client.fetch_user(token_payload["access_token"])
        except DiscordOAuthError as exc:
            raise ApiException(
                status_code=502,
                error_code="DISCORD_OAUTH_FAILED",
                message=str(exc),
            ) from exc

        discord_user_id = int(user_payload["id"])
        username = self._normalize_username(user_payload)
        avatar_hash = user_payload.get("avatar")

        guild_id = self.settings.DISCORD_GUILD_ID
        guild_member_roles: list[int] = []
        guild_roles_payload: list[dict[str, Any]] = []

        if guild_id:
            try:
                guilds = await client.fetch_user_guilds(token_payload["access_token"])
            except DiscordOAuthError as exc:
                raise ApiException(
                    status_code=502,
                    error_code="DISCORD_GUILDS_FETCH_FAILED",
                    message=str(exc),
                ) from exc

            in_guild = any(str(guild.get("id")) == str(guild_id) for guild in guilds)
            if not in_guild:
                raise ApiException(
                    status_code=403,
                    error_code="GUILD_MEMBERSHIP_REQUIRED",
                    message="Authenticated Discord account is not in the configured guild",
                )

            try:
                guild_roles_payload = await client.fetch_guild_roles(guild_id)
                member_payload = await client.fetch_guild_member(
                    guild_id=guild_id,
                    discord_user_id=discord_user_id,
                )
                guild_member_roles = [int(role_id) for role_id in member_payload.get("roles", [])]
            except DiscordOAuthError as exc:
                raise ApiException(
                    status_code=502,
                    error_code="DISCORD_GUILD_SYNC_FAILED",
                    message=str(exc),
                ) from exc

        async with get_session() as session:
            repo = AuthRepository(session)
            user = await repo.upsert_user(
                discord_user_id=discord_user_id,
                username=username,
                avatar_hash=avatar_hash,
            )

            if guild_id and guild_roles_payload:
                normalized_roles = [
                    {
                        "id": int(role["id"]),
                        "name": str(role.get("name", "unknown")),
                        "position": int(role.get("position", 0)),
                        "color_int": int(role.get("color", 0) or 0),
                    }
                    for role in guild_roles_payload
                ]
                await repo.upsert_discord_roles(guild_id=guild_id, roles=normalized_roles)
                await repo.replace_user_roles(user_id=user.id, discord_role_ids=guild_member_roles)

            if discord_user_id in self.settings.owner_discord_ids:
                await repo.set_user_permission(
                    user_id=user.id,
                    permission_key="owner.override",
                    allow=True,
                )

            await repo.touch_user_login(user.id)

            token_ttl_seconds = self.settings.JWT_EXP_MINUTES * 60
            token_jti = random_jti(18)
            access_token, expires_at = create_signed_token(
                settings=self.settings,
                token_type="access",
                claims={
                    "sub": str(user.id),
                    "discord_user_id": discord_user_id,
                    "jti": token_jti,
                },
                ttl_seconds=token_ttl_seconds,
            )
            await repo.create_session(
                user_id=user.id,
                token_jti=token_jti,
                expires_at=expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            permissions = await repo.list_effective_permission_keys(user.id)
            role_ids = await repo.list_user_role_ids(user.id)
            account_link = await repo.get_user_game_account_by_user_id(user.id)

        principal = AuthenticatedPrincipal(
            user_id=user.id,
            discord_user_id=discord_user_id,
            username=username,
            role_ids=tuple(sorted(role_ids)),
            permissions=tuple(sorted(permissions)),
            is_owner="owner.override" in permissions
            or discord_user_id in self.settings.owner_discord_ids,
            is_verified=bool(account_link and account_link.is_verified),
            account_name=account_link.account_name if account_link else None,
            avatar_url=self._build_avatar_url(
                discord_user_id=discord_user_id,
                avatar_hash=avatar_hash,
            ),
            token_jti=token_jti,
        )
        return IssuedAccessToken(access_token=access_token, expires_at=expires_at, token_jti=token_jti), principal

    async def get_principal_from_access_token(self, token: str) -> AuthenticatedPrincipal:
        self._ensure_jwt_config()
        payload = decode_signed_token(
            settings=self.settings,
            token=token,
            expected_type="access",
        )

        try:
            user_id = int(payload["sub"])
            discord_user_id = int(payload["discord_user_id"])
            token_jti = str(payload["jti"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ApiException(
                status_code=401,
                error_code="TOKEN_PAYLOAD_INVALID",
                message="Authentication token payload is invalid",
            ) from exc

        async with get_session() as session:
            repo = AuthRepository(session)
            user = await repo.get_user_by_id(user_id)
            if user is None or not user.is_active:
                raise ApiException(
                    status_code=401,
                    error_code="USER_NOT_ACTIVE",
                    message="Authenticated user is not active",
                )

            db_session = await repo.get_session_by_jti(token_jti)
            now = datetime.now(timezone.utc)
            if (
                db_session is None
                or db_session.is_revoked
                or db_session.expires_at <= now
            ):
                raise ApiException(
                    status_code=401,
                    error_code="SESSION_INVALID",
                    message="Session is invalid or expired",
                )

            permissions = await repo.list_effective_permission_keys(user.id)
            role_ids = await repo.list_user_role_ids(user.id)
            account_link = await repo.get_user_game_account_by_user_id(user.id)

        return AuthenticatedPrincipal(
            user_id=user.id,
            discord_user_id=discord_user_id,
            username=user.username,
            role_ids=tuple(sorted(role_ids)),
            permissions=tuple(sorted(permissions)),
            is_owner="owner.override" in permissions
            or discord_user_id in self.settings.owner_discord_ids,
            is_verified=bool(account_link and account_link.is_verified),
            account_name=account_link.account_name if account_link else None,
            avatar_url=self._build_avatar_url(
                discord_user_id=discord_user_id,
                avatar_hash=user.avatar_hash,
            ),
            token_jti=token_jti,
        )

    async def logout(self, token_jti: str) -> None:
        async with get_session() as session:
            repo = AuthRepository(session)
            await repo.revoke_session(token_jti)

    async def sync_discord_roles(self) -> list[dict[str, Any]]:
        guild_id = self.settings.DISCORD_GUILD_ID
        if guild_id is None:
            raise ApiException(
                status_code=400,
                error_code="DISCORD_GUILD_ID_MISSING",
                message="DISCORD_GUILD_ID must be configured before role sync",
            )
        client = self._oauth_client()
        try:
            roles_payload = await client.fetch_guild_roles(guild_id)
        except DiscordOAuthError as exc:
            raise ApiException(
                status_code=502,
                error_code="DISCORD_ROLE_SYNC_FAILED",
                message=str(exc),
            ) from exc

        normalized_roles = [
            {
                "id": int(role["id"]),
                "name": str(role.get("name", "unknown")),
                "position": int(role.get("position", 0)),
                "color_int": int(role.get("color", 0) or 0),
            }
            for role in roles_payload
        ]

        async with get_session() as session:
            repo = AuthRepository(session)
            saved = await repo.upsert_discord_roles(guild_id=guild_id, roles=normalized_roles)
            return [
                {
                    "discord_role_id": role.discord_role_id,
                    "guild_id": role.guild_id,
                    "name": role.name,
                    "position": role.position,
                    "color_int": role.color_int,
                    "is_active": role.is_active,
                    "synced_at": role.synced_at,
                }
                for role in saved
            ]

    async def list_discord_roles(self) -> list[dict[str, Any]]:
        async with get_session() as session:
            repo = AuthRepository(session)
            roles = await repo.list_discord_roles(guild_id=self.settings.DISCORD_GUILD_ID)
            return [
                {
                    "discord_role_id": role.discord_role_id,
                    "guild_id": role.guild_id,
                    "name": role.name,
                    "position": role.position,
                    "color_int": role.color_int,
                    "is_active": role.is_active,
                    "synced_at": role.synced_at,
                }
                for role in roles
            ]

    @staticmethod
    def _build_avatar_url(*, discord_user_id: int, avatar_hash: str | None) -> str | None:
        if not avatar_hash:
            return None
        return f"https://cdn.discordapp.com/avatars/{discord_user_id}/{avatar_hash}.png?size=256"

    @staticmethod
    def _normalize_username(user_payload: dict[str, Any]) -> str:
        username = str(user_payload.get("username") or "unknown")
        discriminator = str(user_payload.get("discriminator") or "")
        if discriminator and discriminator != "0":
            return f"{username}#{discriminator}"
        global_name = str(user_payload.get("global_name") or "").strip()
        if global_name:
            return global_name
        return username
