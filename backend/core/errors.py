import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.core.request_context import request_id_ctx

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    request_id: str
    details: dict[str, Any] | None = None


class ApiException(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def handle_api_exception(_: Request, exc: ApiException):
        payload = ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=request_id_ctx.get(),
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(_: Request, exc: Exception):
        logger.exception("Unhandled backend exception: %s", exc.__class__.__name__)
        payload = ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="Unexpected server error",
            request_id=request_id_ctx.get(),
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

