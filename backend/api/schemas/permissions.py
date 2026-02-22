from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RolePermissionMatrixItem(BaseModel):
    discord_role_id: str
    guild_id: str
    name: str
    position: int
    is_active: bool
    assigned_permissions: list[str]

    @field_validator("discord_role_id", "guild_id", mode="before")
    @classmethod
    def _cast_snowflake_to_str(cls, value):
        if value is None:
            return ""
        return str(value)


class RolePermissionUpdateRequest(BaseModel):
    permission_keys: list[str] = Field(default_factory=list)
