import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import api_router
from backend.application.services.bootstrap_service import BootstrapService
from backend.core.config import get_settings
from backend.core.database import DatabaseManager
from backend.core.errors import register_exception_handlers
from backend.core.logging import configure_logging
from backend.core.observability import (
    AccessLogMetricsMiddleware,
    AuditTrailMiddleware,
    SecurityHardeningMiddleware,
)
from backend.core.rate_limit import rate_limiter
from backend.core.request_context import RequestContextMiddleware
from backend.infrastructure.cache.redis_cache import cache

logger = logging.getLogger(__name__)


async def _run_bootstrap_seed(app: FastAPI, *, blocking: bool) -> None:
    settings = get_settings()
    attempts = max(1, int(settings.BACKEND_BOOTSTRAP_RETRY_ATTEMPTS))
    retry_delay_seconds = max(1, int(settings.BACKEND_BOOTSTRAP_RETRY_DELAY_SECONDS))
    last_exc: Exception | None = None

    app.state.bootstrap_seed_ready = False
    app.state.bootstrap_seed_last_error = None

    for attempt in range(1, attempts + 1):
        try:
            await BootstrapService().run()
            app.state.bootstrap_seed_ready = True
            app.state.bootstrap_seed_last_error = None
            return
        except asyncio.CancelledError:
            logger.info("Bootstrap seed task cancelled")
            raise
        except Exception as exc:  # pragma: no cover - defensive startup path
            last_exc = exc
            app.state.bootstrap_seed_ready = False
            app.state.bootstrap_seed_last_error = str(exc)
            logger.exception(
                "Bootstrap seed failed (attempt=%s/%s)", attempt, attempts
            )
            if attempt < attempts:
                await asyncio.sleep(retry_delay_seconds)

    if blocking and last_exc is not None:
        raise RuntimeError(
            f"Bootstrap seed failed after {attempts} attempts"
        ) from last_exc


def create_app() -> FastAPI:
    """FastAPI app factory."""
    settings = get_settings()
    configure_logging(settings.BACKEND_LOG_LEVEL, settings.BACKEND_LOG_FORMAT)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await DatabaseManager.initialize()
        app.state.bootstrap_seed_task = None
        app.state.bootstrap_seed_ready = False
        app.state.bootstrap_seed_last_error = None

        if settings.BACKEND_BOOTSTRAP_BLOCKING:
            await _run_bootstrap_seed(app, blocking=True)
        else:
            logger.info("Starting bootstrap seed in background")
            app.state.bootstrap_seed_task = asyncio.create_task(
                _run_bootstrap_seed(app, blocking=False)
            )
        try:
            yield
        finally:
            task = getattr(app.state, "bootstrap_seed_task", None)
            if task is not None and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            await rate_limiter.close()
            await cache.close()
            await DatabaseManager.close()

    app = FastAPI(
        title=settings.BACKEND_APP_NAME,
        version=settings.BACKEND_APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(SecurityHardeningMiddleware, settings=settings)
    app.add_middleware(AuditTrailMiddleware, settings=settings)
    app.add_middleware(AccessLogMetricsMiddleware, settings=settings)
    app.add_middleware(RequestContextMiddleware)
    if settings.BACKEND_CORS_ENABLED:
        # Register CORS last so it wraps the full stack and can short-circuit preflight.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=settings.BACKEND_CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
            expose_headers=settings.cors_expose_headers,
            max_age=settings.BACKEND_CORS_MAX_AGE_SECONDS,
        )
    app.include_router(api_router, prefix=settings.BACKEND_API_PREFIX)
    register_exception_handlers(app)

    return app

