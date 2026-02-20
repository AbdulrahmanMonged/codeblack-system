from __future__ import annotations

import asyncio

from backend.application.services.voting_service import VotingService
from backend.core.celery_app import celery_app
from backend.core.database import DatabaseManager


@celery_app.task(name="backend.tasks.voting_tasks.auto_close_expired")
def auto_close_expired_voting_contexts() -> dict:
    async def _run() -> dict:
        await DatabaseManager.initialize()
        service = VotingService()
        return await service.auto_close_expired_contexts(limit=500)

    return asyncio.run(_run())
