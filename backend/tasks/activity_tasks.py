from __future__ import annotations

from backend.application.services.activity_service import ActivityService
from backend.core.celery_app import celery_app
from backend.core.database import DatabaseManager
from backend.tasks.async_runner import run_async


@celery_app.task(name="backend.tasks.activity_tasks.process_publish_queue")
def process_activity_publish_queue() -> dict:
    async def _run() -> dict:
        await DatabaseManager.initialize()
        service = ActivityService()
        return await service.process_publish_queue_tick()

    return run_async(_run())
