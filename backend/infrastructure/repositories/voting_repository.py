from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.auth import User
from backend.infrastructure.db.models.voting import (
    VotingContext,
    VotingEvent,
    VotingVote,
)


class VotingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_context(self, *, context_type: str, context_id: str) -> VotingContext | None:
        stmt = select(VotingContext).where(
            VotingContext.context_type == context_type,
            VotingContext.context_id == context_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_context(
        self,
        *,
        context_type: str,
        context_id: str,
        opened_by_user_id: int | None,
        title: str | None,
        metadata_json: dict[str, Any] | None,
        auto_close_at,
    ) -> VotingContext:
        row = VotingContext(
            context_type=context_type,
            context_id=context_id,
            status="open",
            opened_by_user_id=opened_by_user_id,
            title=title,
            metadata_json=metadata_json,
            auto_close_at=auto_close_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_or_create_context(
        self,
        *,
        context_type: str,
        context_id: str,
        opened_by_user_id: int | None,
        title: str | None,
        metadata_json: dict[str, Any] | None,
        auto_close_at,
    ) -> tuple[VotingContext, bool]:
        existing = await self.get_context(context_type=context_type, context_id=context_id)
        if existing is not None:
            return existing, False
        created = await self.create_context(
            context_type=context_type,
            context_id=context_id,
            opened_by_user_id=opened_by_user_id,
            title=title,
            metadata_json=metadata_json,
            auto_close_at=auto_close_at,
        )
        return created, True

    async def get_vote_by_user(
        self,
        *,
        voting_context_id: int,
        voter_user_id: int,
    ) -> VotingVote | None:
        stmt = select(VotingVote).where(
            VotingVote.voting_context_id == voting_context_id,
            VotingVote.voter_user_id == voter_user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_vote(
        self,
        *,
        voting_context_id: int,
        voter_user_id: int,
        choice: str,
        comment_text: str | None = None,
    ) -> tuple[VotingVote, str | None]:
        row = await self.get_vote_by_user(
            voting_context_id=voting_context_id,
            voter_user_id=voter_user_id,
        )
        previous_choice = row.choice if row is not None else None
        if row is None:
            row = VotingVote(
                voting_context_id=voting_context_id,
                voter_user_id=voter_user_id,
                choice=choice,
                comment_text=comment_text,
            )
            self.session.add(row)
            await self.session.flush()
            return row, previous_choice

        row.choice = choice
        row.comment_text = comment_text
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return row, previous_choice

    async def list_votes_with_users(
        self,
        *,
        voting_context_id: int,
    ) -> Sequence[tuple[VotingVote, User]]:
        stmt = (
            select(VotingVote, User)
            .join(User, User.id == VotingVote.voter_user_id)
            .where(VotingVote.voting_context_id == voting_context_id)
            .order_by(VotingVote.cast_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def count_votes(
        self,
        *,
        voting_context_id: int,
    ) -> dict[str, int]:
        stmt = (
            select(VotingVote.choice, func.count(VotingVote.id))
            .where(VotingVote.voting_context_id == voting_context_id)
            .group_by(VotingVote.choice)
        )
        result = await self.session.execute(stmt)
        counts: dict[str, int] = {"yes": 0, "no": 0}
        for choice, count in result.all():
            normalized = str(choice).strip().lower()
            if normalized in counts:
                counts[normalized] = int(count)
        counts["total"] = counts["yes"] + counts["no"]
        return counts

    async def reset_votes(
        self,
        *,
        voting_context_id: int,
    ) -> int:
        stmt = delete(VotingVote).where(VotingVote.voting_context_id == voting_context_id)
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def list_expired_open_contexts(
        self,
        *,
        now,
        limit: int,
    ) -> Sequence[VotingContext]:
        stmt = (
            select(VotingContext)
            .where(
                VotingContext.status == "open",
                VotingContext.auto_close_at.is_not(None),
                VotingContext.auto_close_at <= now,
            )
            .order_by(VotingContext.auto_close_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def append_event(
        self,
        *,
        voting_context_id: int,
        event_type: str,
        actor_user_id: int | None,
        target_user_id: int | None,
        vote_choice: str | None,
        reason: str | None,
        metadata_json: dict[str, Any] | None,
    ) -> VotingEvent:
        row = VotingEvent(
            voting_context_id=voting_context_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            vote_choice=vote_choice,
            reason=reason,
            metadata_json=metadata_json,
        )
        self.session.add(row)
        await self.session.flush()
        return row
