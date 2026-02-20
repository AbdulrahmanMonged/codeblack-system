from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConfigEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value_json: Any
    schema_version: int
    is_sensitive: bool
    updated_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ConfigUpsertRequest(BaseModel):
    value_json: Any
    schema_version: int = 1
    is_sensitive: bool = False
    change_reason: str = Field(default="Updated from dashboard", min_length=3)


class ConfigPreviewRequest(BaseModel):
    value_json: Any
    schema_version: int = 1
    is_sensitive: bool = False


class ConfigPreviewResponse(BaseModel):
    valid: bool
    normalized_value: Any
    issues: list[str]


class ConfigRollbackRequest(BaseModel):
    change_id: int
    change_reason: str = Field(default="Rollback requested", min_length=3)


class ConfigMutationResponse(BaseModel):
    key: str
    change_id: int
    applied: bool
    pending_approval: bool
    message: str
    entry: ConfigEntryResponse | None = None


class ConfigApproveRequest(BaseModel):
    change_reason: str = Field(default="Approved by reviewer", min_length=3)


class ConfigChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    config_key: str
    before_json: Any
    after_json: Any
    schema_version: int
    is_sensitive: bool
    changed_by_user_id: int | None = None
    approved_by_user_id: int | None = None
    requires_approval: bool
    status: str
    change_reason: str
    approved_at: datetime | None = None
    created_at: datetime
    change_signature: str | None = None

