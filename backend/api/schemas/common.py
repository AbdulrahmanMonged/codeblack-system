from datetime import datetime
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    version: str
    timestamp: datetime


class OperationResponse(BaseModel):
    ok: bool
    message: str
    details: dict[str, Any] | None = None

