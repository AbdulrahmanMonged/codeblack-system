from __future__ import annotations

from pydantic import BaseModel, Field


class RolePermissionMatrixItem(BaseModel):
    discord_role_id: str
    guild_id: str
    name: str
    position: int
    is_active: bool
    assigned_permissions: list[str]
    available_permissions: list[str]


class RolePermissionUpdateRequest(BaseModel):
    permission_keys: list[str] = Field(default_factory=list)
