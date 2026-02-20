from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class IpcCommandEnvelope(BaseModel):
    type: str
    request_id: str
    actor: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class IpcCommandAck(BaseModel):
    type: Literal["command_ack"] = "command_ack"
    request_id: str
    ok: bool
    applied_at: datetime


class IpcCommandFailed(BaseModel):
    type: Literal["command_failed"] = "command_failed"
    request_id: str
    error_code: str
    message: str
    failed_at: datetime

