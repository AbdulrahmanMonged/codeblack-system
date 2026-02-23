from datetime import datetime, timezone

from backend.core.celery_app import celery_app


@celery_app.task(name="backend.tasks.system_tasks.heartbeat")
def heartbeat() -> str:
    """Simple backend task used to verify shared Celery wiring."""
    return f"backend-heartbeat:{datetime.now(timezone.utc).isoformat()}"
