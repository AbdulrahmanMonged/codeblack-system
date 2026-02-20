from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models.config_registry import (
    ConfigChangeHistory,
    ConfigRegistry,
)


class ConfigRegistryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, *, include_sensitive: bool) -> Sequence[ConfigRegistry]:
        stmt = select(ConfigRegistry).order_by(ConfigRegistry.key.asc())
        if not include_sensitive:
            stmt = stmt.where(ConfigRegistry.is_sensitive == False)  # noqa: E712
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_key(self, key: str) -> ConfigRegistry | None:
        stmt = select(ConfigRegistry).where(ConfigRegistry.key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        key: str,
        value_json: Any,
        schema_version: int,
        is_sensitive: bool,
        updated_by_user_id: int | None,
    ) -> ConfigRegistry:
        entry = await self.get_by_key(key)
        if entry is None:
            entry = ConfigRegistry(
                key=key,
                value_json=value_json,
                schema_version=schema_version,
                is_sensitive=is_sensitive,
                updated_by_user_id=updated_by_user_id,
            )
            self.session.add(entry)
            await self.session.flush()
            return entry

        entry.value_json = value_json
        entry.schema_version = schema_version
        entry.is_sensitive = is_sensitive
        entry.updated_by_user_id = updated_by_user_id
        await self.session.flush()
        return entry

    async def delete_by_key(self, key: str) -> bool:
        stmt = delete(ConfigRegistry).where(ConfigRegistry.key == key)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def add_change(
        self,
        *,
        config_key: str,
        before_json: Any,
        after_json: Any,
        schema_version: int = 1,
        is_sensitive: bool = False,
        changed_by_user_id: int | None,
        change_reason: str,
        approved_by_user_id: int | None = None,
        requires_approval: bool = False,
        status: str = "applied",
        approved_at: datetime | None = None,
    ) -> ConfigChangeHistory:
        change = ConfigChangeHistory(
            config_key=config_key,
            before_json=before_json,
            after_json=after_json,
            schema_version=schema_version,
            is_sensitive=is_sensitive,
            changed_by_user_id=changed_by_user_id,
            approved_by_user_id=approved_by_user_id,
            requires_approval=requires_approval,
            status=status,
            change_reason=change_reason,
            approved_at=approved_at,
        )
        self.session.add(change)
        await self.session.flush()
        return change

    async def list_changes(self, *, limit: int) -> Sequence[ConfigChangeHistory]:
        stmt = (
            select(ConfigChangeHistory)
            .order_by(ConfigChangeHistory.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_change_by_id(self, change_id: int) -> ConfigChangeHistory | None:
        stmt = select(ConfigChangeHistory).where(ConfigChangeHistory.id == change_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_change_approved(
        self,
        *,
        change_id: int,
        approved_by_user_id: int,
        approval_note: str | None = None,
    ) -> ConfigChangeHistory | None:
        change = await self.get_change_by_id(change_id)
        if change is None:
            return None
        change.approved_by_user_id = approved_by_user_id
        change.approved_at = datetime.now(timezone.utc)
        change.status = "applied"
        if approval_note:
            change.change_reason = f"{change.change_reason}\n[APPROVAL] {approval_note}"
        await self.session.flush()
        return change

