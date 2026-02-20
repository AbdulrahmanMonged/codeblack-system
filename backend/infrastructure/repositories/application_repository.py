from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.recruitment import (
    Application,
    ApplicationDecision,
    ApplicationEligibilityState,
)


class ApplicationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_application(self, **kwargs) -> Application:
        application = Application(**kwargs)
        self.session.add(application)
        await self.session.flush()
        return application

    async def get_by_public_id(self, public_id: str) -> Application | None:
        stmt = select(Application).where(Application.public_id == public_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_applications(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[Application]:
        stmt = select(Application).order_by(Application.submitted_at.desc())
        if status:
            stmt = stmt.where(Application.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_decision(
        self,
        *,
        application_id: int,
        reviewer_user_id: int,
        decision: str,
        decision_reason: str,
        reapply_policy: str,
        cooldown_days: int | None,
        reapply_allowed_at: datetime | None,
    ) -> ApplicationDecision:
        row = ApplicationDecision(
            application_id=application_id,
            reviewer_user_id=reviewer_user_id,
            decision=decision,
            decision_reason=decision_reason,
            reapply_policy=reapply_policy,
            cooldown_days=cooldown_days,
            reapply_allowed_at=reapply_allowed_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_eligibility_by_account(
        self,
        account_name: str,
    ) -> ApplicationEligibilityState | None:
        stmt = select(ApplicationEligibilityState).where(
            ApplicationEligibilityState.account_name == account_name
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_eligibility(
        self,
        *,
        account_name: str,
        eligibility_status: str,
        wait_until: datetime | None,
        source: str,
        source_ref_id: str | None,
        player_id: int | None = None,
    ) -> ApplicationEligibilityState:
        row = await self.get_eligibility_by_account(account_name)
        if row is None:
            row = ApplicationEligibilityState(
                account_name=account_name,
                player_id=player_id,
                eligibility_status=eligibility_status,
                wait_until=wait_until,
                source=source,
                source_ref_id=source_ref_id,
            )
            self.session.add(row)
            await self.session.flush()
            return row

        row.player_id = player_id
        row.eligibility_status = eligibility_status
        row.wait_until = wait_until
        row.source = source
        row.source_ref_id = source_ref_id
        await self.session.flush()
        return row

    async def count_recent_submissions_by_ip_hash(self, ip_hash: str, hours: int = 24) -> int:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = select(func.count(Application.id)).where(
            Application.submitter_ip_hash == ip_hash,
            Application.submitted_at >= since,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def list_account_history(
        self,
        *,
        account_name: str,
        limit: int = 10,
    ) -> Sequence[tuple[Application, ApplicationDecision | None]]:
        stmt = (
            select(Application, ApplicationDecision)
            .outerjoin(
                ApplicationDecision,
                ApplicationDecision.application_id == Application.id,
            )
            .where(Application.account_name == account_name)
            .order_by(Application.submitted_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.all()
