"""
Shared Celery configuration used by bot and backend services.
"""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery(
    "codeblack",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    include=[
        "bot.tasks.forum_tasks",
        "bot.tasks.activity_tasks",
        "bot.tasks.maintenance_tasks",
        "backend.tasks.system_tasks",
        "backend.tasks.activity_tasks",
        "backend.tasks.voting_tasks",
    ],
)

celery_app.conf.beat_schedule = {
    "refresh-cf-session": {
        "task": "bot.tasks.maintenance_tasks.refresh_session",
        "schedule": 43200.0,
    },
    "daily-activity-aggregation": {
        "task": "bot.tasks.activity_tasks.aggregate_daily",
        "schedule": crontab(hour=0, minute=5),
    },
    "cleanup-stale-sessions": {
        "task": "bot.tasks.maintenance_tasks.cleanup_stale_sessions",
        "schedule": crontab(hour=6, minute=0),
    },
    "backend-voting-auto-close": {
        "task": "backend.tasks.voting_tasks.auto_close_expired",
        "schedule": 300.0,
    },
    "backend-activities-publish-queue": {
        "task": "backend.tasks.activity_tasks.process_publish_queue",
        "schedule": 60.0,
    },
}
