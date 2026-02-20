"""
Backend-oriented Celery worker entrypoint.

Run with:
    celery -A backend.celery_worker.celery_app worker --loglevel=info
    celery -A backend.celery_worker.celery_app beat --loglevel=info
"""

from backend.core.celery_app import celery_app  # noqa: F401
