from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.auth_repository import AuthRepository
from backend.infrastructure.repositories.config_registry_repository import (
    ConfigRegistryRepository,
)
from backend.infrastructure.repositories.voting_repository import VotingRepository


class VotingService:
    AUTO_CLOSE_CONFIG_KEY = "voting.auto_close_days"
    DEFAULT_AUTO_CLOSE_DAYS = 3
    VALID_CHOICES = {"yes", "no"}
    VALID_STATES = {"open", "closed"}

    async def get_context(
        self,
        *,
        context_type: str,
        context_id: str,
        principal_user_id: int | None,
    ) -> dict:
        normalized_type, normalized_id = self._normalize_context(
            context_type=context_type,
            context_id=context_id,
        )
        async with get_session() as session:
            repo = VotingRepository(session)
            context = await repo.get_context(
                context_type=normalized_type,
                context_id=normalized_id,
            )
            if context is None:
                raise ApiException(
                    status_code=404,
                    error_code="VOTING_CONTEXT_NOT_FOUND",
                    message=f"Voting context {normalized_type}/{normalized_id} not found",
                )
            return await self._context_payload(
                repo=repo,
                context=context,
                principal_user_id=principal_user_id,
            )

    async def cast_vote(
        self,
        *,
        context_type: str,
        context_id: str,
        voter_user_id: int,
        choice: str,
        comment_text: str | None = None,
    ) -> dict:
        normalized_choice = self._normalize_choice(choice)
        normalized_type, normalized_id = self._normalize_context(
            context_type=context_type,
            context_id=context_id,
        )
        async with get_session() as session:
            repo = VotingRepository(session)
            auto_close_days = await self._resolve_auto_close_days(session)
            auto_close_at = datetime.now(timezone.utc) + timedelta(days=auto_close_days)
            context, created = await repo.get_or_create_context(
                context_type=normalized_type,
                context_id=normalized_id,
                opened_by_user_id=voter_user_id,
                title=None,
                metadata_json=None,
                auto_close_at=auto_close_at,
            )
            if created:
                await repo.append_event(
                    voting_context_id=context.id,
                    event_type="context_opened",
                    actor_user_id=voter_user_id,
                    target_user_id=None,
                    vote_choice=None,
                    reason="auto_open_on_first_vote",
                    metadata_json={"auto_close_days": auto_close_days},
                )
            if context.status != "open":
                raise ApiException(
                    status_code=409,
                    error_code="VOTING_CLOSED",
                    message="Voting is closed for this context",
                )

            vote, previous_choice = await repo.upsert_vote(
                voting_context_id=context.id,
                voter_user_id=voter_user_id,
                choice=normalized_choice,
                comment_text=comment_text.strip() if comment_text else None,
            )
            event_type = (
                "vote_cast"
                if previous_choice is None
                else ("vote_changed" if previous_choice != normalized_choice else "vote_cast_noop")
            )
            await repo.append_event(
                voting_context_id=context.id,
                event_type=event_type,
                actor_user_id=voter_user_id,
                target_user_id=voter_user_id,
                vote_choice=normalized_choice,
                reason=None,
                metadata_json={"previous_choice": previous_choice},
            )
            payload = await self._context_payload(
                repo=repo,
                context=context,
                principal_user_id=voter_user_id,
            )
            payload["last_vote"] = {
                "user_id": vote.voter_user_id,
                "choice": vote.choice,
                "comment_text": vote.comment_text,
                "previous_choice": previous_choice,
            }
            return payload

    async def list_voters(
        self,
        *,
        context_type: str,
        context_id: str,
    ) -> dict:
        normalized_type, normalized_id = self._normalize_context(
            context_type=context_type,
            context_id=context_id,
        )
        async with get_session() as session:
            repo = VotingRepository(session)
            auth_repo = AuthRepository(session)
            context = await repo.get_context(
                context_type=normalized_type,
                context_id=normalized_id,
            )
            if context is None:
                raise ApiException(
                    status_code=404,
                    error_code="VOTING_CONTEXT_NOT_FOUND",
                    message=f"Voting context {normalized_type}/{normalized_id} not found",
                )
            votes_with_users = await repo.list_votes_with_users(voting_context_id=context.id)
            counts = await repo.count_votes(voting_context_id=context.id)
            return {
                "context_type": context.context_type,
                "context_id": context.context_id,
                "status": context.status,
                "opened_by_user_id": context.opened_by_user_id,
                "closed_by_user_id": context.closed_by_user_id,
                "opened_at": context.opened_at,
                "closed_at": context.closed_at,
                "close_reason": context.close_reason,
                "auto_close_at": context.auto_close_at,
                "title": context.title,
                "metadata_json": context.metadata_json,
                "counts": counts,
                "voters": [
                    {
                        "user_id": vote.voter_user_id,
                        "discord_user_id": user.discord_user_id,
                        "username": user.username,
                        "avatar_url": self._build_avatar_url(
                            discord_user_id=user.discord_user_id,
                            avatar_hash=user.avatar_hash,
                        ),
                        "name_color_hex": self._to_hex_color(
                            await auth_repo.get_highest_role_color_int(user_id=user.id)
                        ),
                        "choice": vote.choice,
                        "comment_text": vote.comment_text,
                        "cast_at": vote.cast_at,
                        "updated_at": vote.updated_at,
                    }
                    for vote, user in votes_with_users
                ],
            }

    async def close_context(
        self,
        *,
        context_type: str,
        context_id: str,
        actor_user_id: int,
        reason: str | None,
        source: str = "manual",
    ) -> dict:
        return await self._set_context_state(
            context_type=context_type,
            context_id=context_id,
            actor_user_id=actor_user_id,
            target_state="closed",
            reason=reason,
            source=source,
        )

    async def reopen_context(
        self,
        *,
        context_type: str,
        context_id: str,
        actor_user_id: int,
        reason: str | None,
    ) -> dict:
        return await self._set_context_state(
            context_type=context_type,
            context_id=context_id,
            actor_user_id=actor_user_id,
            target_state="open",
            reason=reason,
            source="manual",
        )

    async def reset_context(
        self,
        *,
        context_type: str,
        context_id: str,
        actor_user_id: int,
        reason: str | None,
        reopen: bool,
    ) -> dict:
        normalized_type, normalized_id = self._normalize_context(
            context_type=context_type,
            context_id=context_id,
        )
        async with get_session() as session:
            repo = VotingRepository(session)
            context = await repo.get_context(
                context_type=normalized_type,
                context_id=normalized_id,
            )
            if context is None:
                raise ApiException(
                    status_code=404,
                    error_code="VOTING_CONTEXT_NOT_FOUND",
                    message=f"Voting context {normalized_type}/{normalized_id} not found",
                )

            previous_status = context.status
            removed_count = await repo.reset_votes(voting_context_id=context.id)
            if reopen:
                context.status = "open"
                context.closed_at = None
                context.closed_by_user_id = None
                context.close_reason = None
            await repo.append_event(
                voting_context_id=context.id,
                event_type="context_reset",
                actor_user_id=actor_user_id,
                target_user_id=None,
                vote_choice=None,
                reason=reason,
                metadata_json={
                    "removed_votes": removed_count,
                    "reopen": reopen,
                    "previous_status": previous_status,
                },
            )
            payload = await self._context_payload(
                repo=repo,
                context=context,
                principal_user_id=actor_user_id,
            )
            payload["reset"] = {"removed_votes": removed_count, "reopen": reopen}
            return payload

    async def auto_close_expired_contexts(
        self,
        *,
        limit: int = 250,
    ) -> dict:
        now = datetime.now(timezone.utc)
        async with get_session() as session:
            repo = VotingRepository(session)
            contexts = await repo.list_expired_open_contexts(now=now, limit=limit)
            closed: list[dict] = []
            for context in contexts:
                context.status = "closed"
                context.closed_by_user_id = None
                context.closed_at = now
                context.close_reason = "auto_close_policy"
                await repo.append_event(
                    voting_context_id=context.id,
                    event_type="context_auto_closed",
                    actor_user_id=None,
                    target_user_id=None,
                    vote_choice=None,
                    reason="auto_close_policy",
                    metadata_json={"auto_close_at": context.auto_close_at.isoformat()},
                )
                counts = await repo.count_votes(voting_context_id=context.id)
                closed.append(
                    {
                        "context_type": context.context_type,
                        "context_id": context.context_id,
                        "counts": counts,
                    }
                )
            return {"closed_count": len(closed), "closed": closed}

    async def _set_context_state(
        self,
        *,
        context_type: str,
        context_id: str,
        actor_user_id: int,
        target_state: str,
        reason: str | None,
        source: str,
    ) -> dict:
        normalized_type, normalized_id = self._normalize_context(
            context_type=context_type,
            context_id=context_id,
        )
        if target_state not in self.VALID_STATES:
            raise ApiException(
                status_code=422,
                error_code="INVALID_VOTING_STATE",
                message=f"Invalid target state: {target_state}",
            )
        async with get_session() as session:
            repo = VotingRepository(session)
            context = await repo.get_context(
                context_type=normalized_type,
                context_id=normalized_id,
            )
            if context is None:
                raise ApiException(
                    status_code=404,
                    error_code="VOTING_CONTEXT_NOT_FOUND",
                    message=f"Voting context {normalized_type}/{normalized_id} not found",
                )

            previous_state = context.status
            context.status = target_state
            if target_state == "closed":
                context.closed_by_user_id = actor_user_id
                context.closed_at = datetime.now(timezone.utc)
                context.close_reason = reason
            else:
                context.closed_by_user_id = None
                context.closed_at = None
                context.close_reason = None

            await repo.append_event(
                voting_context_id=context.id,
                event_type=f"context_{target_state}",
                actor_user_id=actor_user_id,
                target_user_id=None,
                vote_choice=None,
                reason=reason,
                metadata_json={
                    "previous_state": previous_state,
                    "source": source,
                },
            )
            payload = await self._context_payload(
                repo=repo,
                context=context,
                principal_user_id=actor_user_id,
            )
            payload["state_transition"] = {
                "from": previous_state,
                "to": target_state,
                "source": source,
            }
            return payload

    async def _context_payload(
        self,
        *,
        repo: VotingRepository,
        context,
        principal_user_id: int | None,
    ) -> dict:
        my_vote = None
        if principal_user_id is not None:
            vote_row = await repo.get_vote_by_user(
                voting_context_id=context.id,
                voter_user_id=principal_user_id,
            )
            if vote_row is not None:
                my_vote = vote_row.choice
        counts = await repo.count_votes(voting_context_id=context.id)
        return {
            "context_type": context.context_type,
            "context_id": context.context_id,
            "status": context.status,
            "opened_by_user_id": context.opened_by_user_id,
            "closed_by_user_id": context.closed_by_user_id,
            "opened_at": context.opened_at,
            "closed_at": context.closed_at,
            "close_reason": context.close_reason,
            "auto_close_at": context.auto_close_at,
            "title": context.title,
            "metadata_json": context.metadata_json,
            "counts": counts,
            "my_vote": my_vote,
        }

    async def _resolve_auto_close_days(self, session) -> int:
        config_repo = ConfigRegistryRepository(session)
        row = await config_repo.get_by_key(self.AUTO_CLOSE_CONFIG_KEY)
        if row and isinstance(row.value_json, int):
            return max(1, min(30, row.value_json))
        return self.DEFAULT_AUTO_CLOSE_DAYS

    def _normalize_choice(self, choice: str) -> str:
        normalized = choice.strip().lower()
        if normalized not in self.VALID_CHOICES:
            raise ApiException(
                status_code=422,
                error_code="INVALID_VOTE_CHOICE",
                message=f"choice must be one of: {sorted(self.VALID_CHOICES)}",
            )
        return normalized

    @staticmethod
    def _build_avatar_url(*, discord_user_id: int, avatar_hash: str | None) -> str | None:
        if not avatar_hash:
            return None
        return f"https://cdn.discordapp.com/avatars/{discord_user_id}/{avatar_hash}.png?size=128"

    @staticmethod
    def _to_hex_color(color_int: int | None) -> str | None:
        if color_int is None:
            return None
        color_int = max(0, min(0xFFFFFF, int(color_int)))
        return f"#{color_int:06X}"

    @staticmethod
    def _normalize_context(*, context_type: str, context_id: str) -> tuple[str, str]:
        normalized_type = context_type.strip().lower()
        normalized_id = context_id.strip()
        if not normalized_type:
            raise ApiException(
                status_code=422,
                error_code="VOTING_CONTEXT_TYPE_INVALID",
                message="context_type cannot be empty",
            )
        if not normalized_id:
            raise ApiException(
                status_code=422,
                error_code="VOTING_CONTEXT_ID_INVALID",
                message="context_id cannot be empty",
            )
        return normalized_type, normalized_id
