from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from backend.api.schemas.config_registry import (
    ConfigChangeResponse,
    ConfigEntryResponse,
    ConfigMutationResponse,
    ConfigPreviewResponse,
)
from backend.core.config import get_settings
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.domain.permissions.catalog import CRITICAL_CONFIG_KEYS
from backend.domain.policies.config_guardrails import ConfigGuardrails
from backend.application.services.notification_service import NotificationService
from backend.infrastructure.repositories.config_registry_repository import (
    ConfigRegistryRepository,
)


class ConfigRegistryService:
    """Use-cases around configuration-as-data and audited config mutation."""

    SECRET_LIKE_MARKERS = (
        "secret",
        "token",
        "password",
        "access_key",
        "private_key",
        "client_secret",
    )
    MASKED_VALUE = "***MASKED***"

    def __init__(self) -> None:
        self.settings = get_settings()

    async def list_entries(self, include_sensitive: bool) -> list[ConfigEntryResponse]:
        async with get_session() as session:
            repo = ConfigRegistryRepository(session)
            entries = await repo.list_entries(include_sensitive=include_sensitive)
            return [ConfigEntryResponse.model_validate(entry) for entry in entries]

    async def upsert_entry(
        self,
        *,
        key: str,
        value_json: Any,
        schema_version: int,
        is_sensitive: bool,
        actor_user_id: int | None,
        change_reason: str,
    ) -> ConfigMutationResponse:
        self._assert_dashboard_key_allowed(key)
        preview = ConfigGuardrails.validate(key=key, value_json=value_json)
        if preview["issues"]:
            raise ApiException(
                status_code=422,
                error_code="CONFIG_VALIDATION_FAILED",
                message="Config validation failed",
                details={"issues": preview["issues"]},
            )

        async with get_session() as session:
            repo = ConfigRegistryRepository(session)
            notification_service = NotificationService()
            existing = await repo.get_by_key(key)
            before_json = existing.value_json if existing else None
            is_critical = key in CRITICAL_CONFIG_KEYS
            if is_critical:
                if actor_user_id is None:
                    raise ApiException(
                        status_code=401,
                        error_code="ACTOR_REQUIRED",
                        message="Critical configuration change requires authenticated actor",
                    )
                change = await repo.add_change(
                    config_key=key,
                    before_json=before_json,
                    after_json=preview["normalized_value"],
                    schema_version=schema_version,
                    is_sensitive=is_sensitive,
                    changed_by_user_id=actor_user_id,
                    change_reason=change_reason,
                    requires_approval=True,
                    status="pending_approval",
                )
                await notification_service.dispatch_in_session(
                    session=session,
                    actor_user_id=actor_user_id,
                    event_type="config.change.pending_approval",
                    category="config",
                    severity="warning",
                    title=f"Config change pending approval: {key}",
                    body=f"Critical config change for {key} was submitted and is waiting for approval.",
                    entity_type="config_key",
                    entity_public_id=key,
                    metadata_json={
                        "change_id": change.id,
                        "status": change.status,
                        "requires_approval": change.requires_approval,
                    },
                )
                current_entry = (
                    ConfigEntryResponse.model_validate(existing) if existing else None
                )
                return ConfigMutationResponse(
                    key=key,
                    change_id=change.id,
                    applied=False,
                    pending_approval=True,
                    message="Critical config change queued for approval",
                    entry=current_entry,
                )

            entry = await repo.upsert(
                key=key,
                value_json=preview["normalized_value"],
                schema_version=schema_version,
                is_sensitive=is_sensitive,
                updated_by_user_id=actor_user_id,
            )
            change = await repo.add_change(
                config_key=key,
                before_json=before_json,
                after_json=entry.value_json,
                schema_version=schema_version,
                is_sensitive=is_sensitive,
                changed_by_user_id=actor_user_id,
                change_reason=change_reason,
                requires_approval=False,
                status="applied",
            )
            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=actor_user_id,
                event_type="config.change.applied",
                category="config",
                severity="info",
                title=f"Config updated: {key}",
                body=f"Configuration key {key} was updated.",
                entity_type="config_key",
                entity_public_id=key,
                metadata_json={
                    "change_id": change.id,
                    "status": change.status,
                    "requires_approval": change.requires_approval,
                },
            )
            return ConfigMutationResponse(
                key=key,
                change_id=change.id,
                applied=True,
                pending_approval=False,
                message="Config updated",
                entry=ConfigEntryResponse.model_validate(entry),
            )

    async def preview_entry(
        self,
        *,
        key: str,
        value_json: Any,
        schema_version: int,
        is_sensitive: bool,
    ) -> ConfigPreviewResponse:
        self._assert_dashboard_key_allowed(key)
        _ = schema_version, is_sensitive  # reserved for future schema checks
        preview = ConfigGuardrails.validate(key=key, value_json=value_json)
        return ConfigPreviewResponse(
            valid=not preview["issues"],
            normalized_value=preview["normalized_value"],
            issues=preview["issues"],
        )

    async def list_changes(
        self,
        *,
        limit: int,
        include_sensitive_values: bool,
    ) -> list[ConfigChangeResponse]:
        async with get_session() as session:
            repo = ConfigRegistryRepository(session)
            changes = await repo.list_changes(limit=limit)
            results: list[ConfigChangeResponse] = []
            for change in changes:
                before_json = change.before_json
                after_json = change.after_json
                should_mask = (
                    change.is_sensitive or self._is_secret_like_key(change.config_key)
                ) and not include_sensitive_values
                if should_mask:
                    before_json = self._mask_sensitive_value(before_json)
                    after_json = self._mask_sensitive_value(after_json)

                signature = self._sign_change_metadata(
                    id=change.id,
                    config_key=change.config_key,
                    before_json=before_json,
                    after_json=after_json,
                    schema_version=change.schema_version,
                    is_sensitive=change.is_sensitive,
                    changed_by_user_id=change.changed_by_user_id,
                    approved_by_user_id=change.approved_by_user_id,
                    requires_approval=change.requires_approval,
                    status=change.status,
                    change_reason=change.change_reason,
                    approved_at=change.approved_at.isoformat()
                    if change.approved_at
                    else None,
                    created_at=change.created_at.isoformat(),
                )

                results.append(
                    ConfigChangeResponse(
                        id=change.id,
                        config_key=change.config_key,
                        before_json=before_json,
                        after_json=after_json,
                        schema_version=change.schema_version,
                        is_sensitive=change.is_sensitive,
                        changed_by_user_id=change.changed_by_user_id,
                        approved_by_user_id=change.approved_by_user_id,
                        requires_approval=change.requires_approval,
                        status=change.status,
                        change_reason=change.change_reason,
                        approved_at=change.approved_at,
                        created_at=change.created_at,
                        change_signature=signature,
                    )
                )
            return results

    async def rollback_to_change(
        self,
        *,
        key: str,
        change_id: int,
        actor_user_id: int | None,
        change_reason: str,
    ) -> None:
        self._assert_dashboard_key_allowed(key)
        async with get_session() as session:
            repo = ConfigRegistryRepository(session)
            notification_service = NotificationService()
            change = await repo.get_change_by_id(change_id)
            if change is None:
                raise ApiException(
                    status_code=404,
                    error_code="CHANGE_NOT_FOUND",
                    message=f"Change id {change_id} not found",
                )
            if change.config_key != key:
                raise ApiException(
                    status_code=400,
                    error_code="CONFIG_KEY_MISMATCH",
                    message="Change record does not match config key",
                )

            existing = await repo.get_by_key(key)
            current_value = existing.value_json if existing else None

            if change.before_json is None:
                await repo.delete_by_key(key)
                new_value = None
            else:
                preview = ConfigGuardrails.validate(
                    key=key, value_json=change.before_json
                )
                if preview["issues"]:
                    raise ApiException(
                        status_code=422,
                        error_code="ROLLBACK_VALIDATION_FAILED",
                        message="Rollback target is invalid by current policy",
                        details={"issues": preview["issues"]},
                    )
                rolled = await repo.upsert(
                    key=key,
                    value_json=preview["normalized_value"],
                    schema_version=1,
                    is_sensitive=False,
                    updated_by_user_id=actor_user_id,
                )
                new_value = rolled.value_json

            await repo.add_change(
                config_key=key,
                before_json=current_value,
                after_json=new_value,
                schema_version=1,
                is_sensitive=False,
                changed_by_user_id=actor_user_id,
                change_reason=change_reason,
                requires_approval=False,
                status="applied",
            )
            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=actor_user_id,
                event_type="config.change.rolled_back",
                category="config",
                severity="warning",
                title=f"Config rolled back: {key}",
                body=f"Configuration key {key} was rolled back to a previous value.",
                entity_type="config_key",
                entity_public_id=key,
                metadata_json={"source_change_id": change_id},
            )

    async def approve_change(
        self,
        *,
        change_id: int,
        approver_user_id: int | None,
        change_reason: str,
    ) -> ConfigMutationResponse:
        if approver_user_id is None:
            raise ApiException(
                status_code=401,
                error_code="APPROVER_REQUIRED",
                message="Approval endpoint requires authenticated actor",
            )

        async with get_session() as session:
            repo = ConfigRegistryRepository(session)
            notification_service = NotificationService()
            change = await repo.get_change_by_id(change_id)
            if change is None:
                raise ApiException(
                    status_code=404,
                    error_code="CHANGE_NOT_FOUND",
                    message=f"Change id {change_id} not found",
                )
            self._assert_dashboard_key_allowed(change.config_key)
            if not change.requires_approval:
                raise ApiException(
                    status_code=400,
                    error_code="CHANGE_NOT_REQUIRING_APPROVAL",
                    message="This config change does not require approval",
                )
            if change.status != "pending_approval":
                raise ApiException(
                    status_code=400,
                    error_code="CHANGE_NOT_PENDING",
                    message=f"Change status must be pending_approval, got {change.status}",
                )
            if (
                change.changed_by_user_id is not None
                and change.changed_by_user_id == approver_user_id
            ):
                raise ApiException(
                    status_code=403,
                    error_code="TWO_STEP_APPROVAL_REQUIRED",
                    message="Editor and approver must be different users",
                )

            preview = ConfigGuardrails.validate(
                key=change.config_key,
                value_json=change.after_json,
            )
            if preview["issues"]:
                raise ApiException(
                    status_code=422,
                    error_code="CONFIG_VALIDATION_FAILED",
                    message="Approved value does not satisfy current guardrails",
                    details={"issues": preview["issues"]},
                )

            entry = await repo.upsert(
                key=change.config_key,
                value_json=preview["normalized_value"],
                schema_version=change.schema_version,
                is_sensitive=change.is_sensitive,
                updated_by_user_id=change.changed_by_user_id,
            )
            await repo.mark_change_approved(
                change_id=change.id,
                approved_by_user_id=approver_user_id,
                approval_note=change_reason,
            )
            await notification_service.dispatch_in_session(
                session=session,
                actor_user_id=approver_user_id,
                event_type="config.change.approved",
                category="config",
                severity="success",
                title=f"Config change approved: {change.config_key}",
                body=f"Pending config change for {change.config_key} was approved and applied.",
                entity_type="config_key",
                entity_public_id=change.config_key,
                metadata_json={"change_id": change.id},
            )
            return ConfigMutationResponse(
                key=change.config_key,
                change_id=change.id,
                applied=True,
                pending_approval=False,
                message="Pending config change approved and applied",
                entry=ConfigEntryResponse.model_validate(entry),
            )

    def _assert_dashboard_key_allowed(self, key: str) -> None:
        if self._is_secret_like_key(key):
            raise ApiException(
                status_code=403,
                error_code="CONFIG_KEY_RESTRICTED",
                message=(
                    "Secret-like config keys cannot be edited from dashboard API; "
                    "use environment/secret manager instead"
                ),
                details={"key": key},
            )

    def _is_secret_like_key(self, key: str) -> bool:
        normalized = key.strip().lower()
        return any(marker in normalized for marker in self.SECRET_LIKE_MARKERS)

    def _mask_sensitive_value(self, value: Any) -> Any:
        if value is None:
            return None
        return self.MASKED_VALUE

    def _sign_change_metadata(self, **payload: Any) -> str:
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        secret = (self.settings.JWT_SECRET or "REDACTED-dev-signing").encode("utf-8")
        digest = hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest


