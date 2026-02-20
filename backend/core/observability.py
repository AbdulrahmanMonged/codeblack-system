from __future__ import annotations

import logging
from time import perf_counter

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.config import BackendSettings, get_settings
from backend.core.errors import ErrorResponse
from backend.core.metrics import metrics_registry
from backend.core.rate_limit import rate_limiter
from backend.core.request_context import request_id_ctx
from backend.core.database import get_session
from backend.infrastructure.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class AccessLogMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: BackendSettings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next):
        started = perf_counter()
        status_code = 500
        response = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route_path = _route_path(request)
            duration_seconds = max(0.0, perf_counter() - started)
            metrics_registry.record_http_request(
                method=request.method,
                route_path=route_path,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
            if self.settings.BACKEND_ENABLE_ACCESS_LOG:
                logger.info(
                    "http_request method=%s path=%s route=%s status=%s duration_ms=%.2f ip=%s",
                    request.method,
                    request.url.path,
                    route_path,
                    status_code,
                    duration_seconds * 1000.0,
                    _client_identity(request),
                )


class SecurityHardeningMiddleware(BaseHTTPMiddleware):
    PRIVILEGED_PREFIXES = ("/admin", "/config", "/permissions", "/bot")
    HIGH_RISK_MUTATION_MARKERS = (
        "/decision",
        "/approve",
        "/deny",
        "/remove",
        "/rollback",
        "/returned",
        "/cancel",
    )

    def __init__(self, app, settings: BackendSettings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        scope, limit, window_seconds = self._resolve_scope(method=method, path=path)
        identity = _client_identity(request)

        if self.settings.BACKEND_RATE_LIMIT_ENABLED and method != "OPTIONS":
            allowed, observed_count = await rate_limiter.check_limit(
                scope=scope,
                identity=identity,
                limit=limit,
                window_seconds=window_seconds,
            )
            if not allowed:
                metrics_registry.record_rate_limit_rejection(scope=scope)
                payload = ErrorResponse(
                    error_code="RATE_LIMITED",
                    message="Too many requests for this endpoint scope",
                    request_id=request_id_ctx.get(),
                    details={
                        "scope": scope,
                        "limit": limit,
                        "window_seconds": window_seconds,
                        "observed_count": observed_count,
                    },
                ).model_dump()
                return JSONResponse(
                    status_code=429,
                    content=payload,
                    headers={"Retry-After": str(window_seconds)},
                )

        response = await call_next(request)

        if (
            self.settings.BACKEND_ANOMALY_THRESHOLD > 0
            and scope in {"auth", "privileged"}
            and response.status_code in {401, 403}
        ):
            metrics_registry.record_authz_failure(
                scope=scope,
                status_code=response.status_code,
            )
            failure_count = await rate_limiter.record_authz_failure(
                scope=scope,
                identity=identity,
                window_seconds=max(1, self.settings.BACKEND_ANOMALY_WINDOW_SECONDS),
            )
            if failure_count >= self.settings.BACKEND_ANOMALY_THRESHOLD:
                if failure_count % self.settings.BACKEND_ANOMALY_THRESHOLD == 0:
                    logger.warning(
                        "authorization anomaly detected scope=%s ip=%s failures=%s window=%ss",
                        scope,
                        identity,
                        failure_count,
                        self.settings.BACKEND_ANOMALY_WINDOW_SECONDS,
                    )

        return response

    def _resolve_scope(self, *, method: str, path: str) -> tuple[str, int, int]:
        api_prefix = self.settings.BACKEND_API_PREFIX.rstrip("/")
        if not path.startswith(api_prefix):
            return "external", max(1, self.settings.BACKEND_RATE_LIMIT_MAX_REQUESTS), max(
                1, self.settings.BACKEND_RATE_LIMIT_WINDOW_SECONDS
            )

        auth_prefix = f"{api_prefix}/auth/discord"
        if path.startswith(auth_prefix):
            return (
                "auth",
                max(1, self.settings.BACKEND_RATE_LIMIT_AUTH_MAX_REQUESTS),
                max(1, self.settings.BACKEND_RATE_LIMIT_WINDOW_SECONDS),
            )

        privileged_root = any(
            path.startswith(f"{api_prefix}{segment}") for segment in self.PRIVILEGED_PREFIXES
        )
        high_risk_marker = any(marker in path for marker in self.HIGH_RISK_MUTATION_MARKERS)
        privileged_mutation = method in {"POST", "PUT", "PATCH", "DELETE"} and (
            privileged_root or high_risk_marker
        )
        if privileged_mutation:
            return (
                "privileged",
                max(1, self.settings.BACKEND_RATE_LIMIT_PRIVILEGED_MAX_REQUESTS),
                max(1, self.settings.BACKEND_RATE_LIMIT_WINDOW_SECONDS),
            )

        return (
            "general",
            max(1, self.settings.BACKEND_RATE_LIMIT_MAX_REQUESTS),
            max(1, self.settings.BACKEND_RATE_LIMIT_WINDOW_SECONDS),
        )


class AuditTrailMiddleware(BaseHTTPMiddleware):
    AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    SKIP_PREFIXES = {"/config"}
    ACTION_SEGMENTS = {
        "decision",
        "approve",
        "deny",
        "reject",
        "remove",
        "rollback",
        "reopen",
        "reset",
        "cancel",
        "returned",
        "sync",
        "preview",
        "trigger",
        "replay",
    }

    def __init__(self, app, settings: BackendSettings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if not self.settings.BACKEND_AUDIT_ENABLED:
            return response
        method = request.method.upper()
        if method not in self.AUDIT_METHODS:
            return response

        entity_type, entity_id, action = self._resolve_event_dimensions(
            request.url.path, method
        )
        if entity_type is None:
            return response

        principal = getattr(request.state, "authenticated_principal", None)
        actor_user_id = getattr(principal, "user_id", None)
        request_id = request_id_ctx.get()

        details = {
            "method": method,
            "path": request.url.path,
            "query": request.url.query or None,
            "status_code": response.status_code,
            "client_ip": _client_identity(request),
        }

        try:
            async with get_session() as session:
                repo = AuditRepository(session)
                await repo.create_event(
                    event_type=f"http.{entity_type}.{action}",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    action=action,
                    actor_user_id=actor_user_id,
                    request_id=request_id,
                    details_json=details,
                )
        except Exception:
            logger.exception(
                "Failed to persist audit event entity_type=%s action=%s path=%s",
                entity_type,
                action,
                request.url.path,
            )

        return response

    def _resolve_event_dimensions(
        self,
        path: str,
        method: str,
    ) -> tuple[str | None, str | None, str]:
        api_prefix = self.settings.BACKEND_API_PREFIX.rstrip("/")
        if not path.startswith(api_prefix):
            return None, None, method.lower()

        relative = path[len(api_prefix) :]
        if not relative.startswith("/"):
            return None, None, method.lower()

        for skip_prefix in self.SKIP_PREFIXES:
            if relative.startswith(skip_prefix):
                return None, None, method.lower()

        segments = [segment for segment in relative.split("/") if segment]
        if not segments:
            return None, None, method.lower()
        entity_type = segments[0]

        action = method.lower()
        if len(segments) >= 2 and segments[-1] in self.ACTION_SEGMENTS:
            action = segments[-1]

        entity_id: str | None = None
        for segment in reversed(segments[1:]):
            if segment in self.ACTION_SEGMENTS:
                continue
            entity_id = segment
            break

        return entity_type, entity_id, action


def _client_identity(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return request.url.path
