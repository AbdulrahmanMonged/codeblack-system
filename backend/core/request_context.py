import contextvars
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Injects request ID into context and response headers."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)

