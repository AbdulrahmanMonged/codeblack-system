import asyncio
from datetime import datetime, timezone
from time import perf_counter

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from redis.asyncio import Redis
from sqlalchemy import text

from backend.api.deps.auth import require_permissions
from backend.api.schemas.common import HealthResponse
from backend.core.config import get_settings
from backend.core.celery_app import celery_app
from backend.core.database import get_session
from backend.core.metrics import metrics_registry

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.BACKEND_APP_NAME,
        environment=settings.BACKEND_ENV,
        version=settings.BACKEND_APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/deep")
async def deep_health(
    _: object = Depends(require_permissions("system.read")),
):
    settings = get_settings()
    overall = "ok"
    checks: dict[str, dict] = {}

    db_started = perf_counter()
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "ok",
            "latency_ms": round((perf_counter() - db_started) * 1000.0, 3),
        }
    except Exception as exc:
        checks["database"] = {
            "status": "fail",
            "error": exc.__class__.__name__,
        }
        overall = _merge_status(overall, "fail")

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_started = perf_counter()
    try:
        await redis.ping()
        checks["redis"] = {
            "status": "ok",
            "latency_ms": round((perf_counter() - redis_started) * 1000.0, 3),
        }

        prefix = settings.IPC_STREAM_PREFIX
        command_stream = f"{prefix}:stream:commands"
        response_stream = f"{prefix}:stream:responses"
        event_stream = f"{prefix}:stream:events"
        dead_letter_stream = f"{prefix}:stream:commands:dlq"
        dead_letter_replay_stream = f"{prefix}:stream:commands:dlq:replay"
        stream_lengths: dict[str, int | None] = {}
        missing_streams: list[str] = []
        for stream_name in (
            command_stream,
            response_stream,
            event_stream,
            dead_letter_stream,
            dead_letter_replay_stream,
        ):
            try:
                stream_lengths[stream_name] = int(await redis.xlen(stream_name))
            except Exception:
                stream_lengths[stream_name] = None
                missing_streams.append(stream_name)
        ipc_status = "ok" if not missing_streams else "degraded"
        checks["ipc"] = {
            "status": ipc_status,
            "stream_lengths": stream_lengths,
            "missing_streams": missing_streams,
        }
        overall = _merge_status(overall, ipc_status)
    except Exception as exc:
        checks["redis"] = {
            "status": "fail",
            "error": exc.__class__.__name__,
        }
        checks["ipc"] = {
            "status": "fail",
            "error": "redis_unavailable",
        }
        overall = _merge_status(overall, "fail")
    finally:
        await redis.aclose()

    celery_started = perf_counter()
    try:
        ping_result = await asyncio.to_thread(
            lambda: celery_app.control.inspect(timeout=1.5).ping()
        )
        if ping_result:
            checks["celery"] = {
                "status": "ok",
                "worker_count": len(ping_result.keys()),
                "latency_ms": round((perf_counter() - celery_started) * 1000.0, 3),
            }
        else:
            checks["celery"] = {
                "status": "degraded",
                "worker_count": 0,
                "detail": "No responding Celery workers",
            }
            overall = _merge_status(overall, "degraded")
    except Exception as exc:
        checks["celery"] = {
            "status": "degraded",
            "error": exc.__class__.__name__,
        }
        overall = _merge_status(overall, "degraded")

    return {
        "status": overall,
        "service": settings.BACKEND_APP_NAME,
        "environment": settings.BACKEND_ENV,
        "version": settings.BACKEND_APP_VERSION,
        "timestamp": datetime.now(timezone.utc),
        "checks": checks,
    }


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics(
    _: object = Depends(require_permissions("system.read")),
):
    settings = get_settings()
    if not settings.BACKEND_ENABLE_METRICS:
        return PlainTextResponse("metrics disabled\n", status_code=503)
    return PlainTextResponse(
        metrics_registry.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/bot-status")
async def bot_status(
    _: object = Depends(require_permissions("bot.read_status")),
):
    settings = get_settings()
    prefix = settings.IPC_STREAM_PREFIX
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        runtime_features = await redis.hgetall(f"{prefix}:runtime:features")
        runtime_channels = await redis.hgetall(f"{prefix}:runtime:channels")
    finally:
        await redis.aclose()
    return {
        "ok": True,
        "broker_url": settings.CELERY_BROKER_URL,
        "result_backend": settings.CELERY_RESULT_BACKEND,
        "ack_timeout_seconds": settings.BOT_COMMAND_ACK_TIMEOUT_SECONDS,
        "registered_tasks_count": len(celery_app.tasks.keys()),
        "runtime_features": runtime_features,
        "runtime_channels": runtime_channels,
        "timestamp": datetime.now(timezone.utc),
    }


def _merge_status(current: str, incoming: str) -> str:
    order = {"ok": 0, "degraded": 1, "fail": 2}
    return incoming if order[incoming] > order[current] else current

