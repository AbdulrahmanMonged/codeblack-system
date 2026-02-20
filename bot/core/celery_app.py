"""
Celery application import for bot runtime.

This module intentionally delegates configuration to a shared module so
backend and bot services use the same broker/backend/task schedule settings.
"""

from shared.celery_shared import celery_app

__all__ = ["celery_app"]
