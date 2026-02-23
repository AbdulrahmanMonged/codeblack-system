"""
Backend Celery entrypoint reusing shared Celery configuration.

This keeps broker/backend settings and worker behavior centralized so the same
Celery worker/beat setup can process both bot and backend tasks.
"""

from shared.celery_shared import celery_app as shared_celery_app

celery_app = shared_celery_app

# Discover backend tasks in the same worker process.
celery_app.autodiscover_tasks(["backend.tasks"], force=True)
