"""
Celery worker entry point.

Run with:
    celery -A celery_worker.celery_app worker --loglevel=info
    celery -A celery_worker.celery_app beat --loglevel=info

Or combined:
    celery -A celery_worker.celery_app worker --beat --loglevel=info
"""

import dotenv

dotenv.load_dotenv()

from shared.celery_shared import celery_app  # noqa: E402, F401
