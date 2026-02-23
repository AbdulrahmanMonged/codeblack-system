from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from backend.application.dto.auth import AuthenticatedPrincipal
from backend.core.config import get_settings
from backend.core.database import get_session
from backend.core.errors import ApiException
from backend.infrastructure.repositories.application_repository import (
    ApplicationRepository,
)
from backend.infrastructure.repositories.blacklist_repository import BlacklistRepository
from backend.infrastructure.repositories.config_registry_repository import (
    ConfigRegistryRepository,
)
from backend.infrastructure.repositories.auth_repository import AuthRepository
from backend.infrastructure.repositories.voting_repository import VotingRepository
from backend.application.services.notification_service import NotificationService


class ApplicationService:
    DEFAULT_COOLDOWN_DAYS = 7
    DEFAULT_GUEST_LIMIT_PER_24H = 3
    DEFAULT_CAPTCHA_ENABLED = False
    DEFAULT_CAPTCHA_SITE_KEY = ""
    COOLDOWN_CONFIG_KEY = "applications.default_denial_cooldown_days"
    GUEST_RATE_LIMIT_CONFIG_KEY = "applications.guest_max_submissions_per_24h"
    CAPTCHA_ENABLED_CONFIG_KEY = "applications.captcha_enabled"
    CAPTCHA_SITE_KEY_CONFIG_KEY = "applications.captcha_site_key"
    VOTING_AUTO_CLOSE_DAYS_CONFIG_KEY = "voting.auto_close_days"
    DEFAULT_VOTING_AUTO_CLOSE_DAYS = 3
    PENDING_APPLICATION_STATUSES = frozenset({"submitted", "pending", "under_review"})

    def __init__(self):
        self.settings = get_settings()

    async def submit_application(
        self,
        *,
        payload: dict,
        principal: AuthenticatedPrincipal | None,
        ip_address: str | None,
        captcha_token: str | None,
    ) -> dict:
        account_name = self._normalize_account_name(payload["account_name"])
        eligibility = await self.check_eligibility(account_name=account_name)
        if not eligibility["allowed"]:
            raise ApiException(
                status_code=403,
                error_code="APPLICATION_NOT_ELIGIBLE",
                message="Applicant is not currently eligible to submit an application",
                details=eligibility,
            )

        policies = await self.get_policies()
        submitter_type = "member" if principal is not None else "guest"
        ip_hash = self._hash_ip(ip_address) if ip_address else None

        async with get_session() as session:
            repo = ApplicationRepository(session)
            voting_repo = VotingRepository(session)
            config_repo = ConfigRegistryRepository(session)
            auth_repo = AuthRepository(session)
            notification_service = NotificationService()
            if submitter_type == "guest" and ip_hash:
                recent_submissions = await repo.count_recent_submissions_by_ip_hash(ip_hash)
                if recent_submissions >= policies["guest_max_submissions_per_24h"]:
                    raise ApiException(
                        status_code=429,
                        error_code="APPLICATION_RATE_LIMITED",
                        message="Too many guest submissions from this IP in the last 24h",
                        details={"max_per_24h": policies["guest_max_submissions_per_24h"]},
                    )
            if submitter_type == "guest" and policies["captcha_enabled"]:
                await self._verify_captcha_token(
                    captcha_token=captcha_token,
                    ip_address=ip_address,
                )

            application = await repo.create_application(
                public_id=self._generate_public_id(),
                status="submitted",
                applicant_discord_id=principal.discord_user_id if principal else None,
                player_id=None,
                submitter_type=submitter_type,
                submitter_ip_hash=ip_hash,
                in_game_nickname=payload["in_game_nickname"],
                account_name=account_name,
                mta_serial=payload["mta_serial"],
                english_skill=payload["english_skill"],
                has_second_account=payload["has_second_account"],
                second_account_name=payload.get("second_account_name"),
                cit_journey=payload["cit_journey"],
                former_groups_reason=payload["former_groups_reason"],
                why_join=payload["why_join"],
                punishlog_url=payload["punishlog_url"],
                stats_url=payload["stats_url"],
                history_url=payload["history_url"],
            )
            auto_close_days = await self._resolve_voting_auto_close_days(config_repo)
            auto_close_at = datetime.now(timezone.utc) + timedelta(days=auto_close_days)
            voting_context, created = await voting_repo.get_or_create_context(
                context_type="application",
                context_id=application.public_id,
                opened_by_user_id=principal.user_id if principal else None,
                title=f"Application Vote: {application.in_game_nickname}",
                metadata_json={
                    "application_public_id": application.public_id,
                    "account_name": application.account_name,
                    "submitter_type": submitter_type,
                },
                auto_close_at=auto_close_at,
            )
            if created:
                await voting_repo.append_event(
                    voting_context_id=voting_context.id,
                    event_type="context_opened",
                    actor_user_id=principal.user_id if principal else None,
                    target_user_id=None,
                    vote_choice=None,
                    reason="application_submitted",
                    metadata_json={"auto_close_days": auto_close_days},
                )

            voter_recipients = await auth_repo.list_active_user_ids_with_any_permissions(
                permission_keys={"voting.cast", "owner.override"},
            )
            if voter_recipients:
                await notification_service.dispatch_in_session(
                    session=session,
                    actor_user_id=principal.user_id if principal else None,
                    event_type="applications.vote_required",
                    category="applications",
                    severity="info",
                    title=f"Vote required: {application.in_game_nickname}",
                    body=(
                        f"Application {application.public_id} was submitted and requires voting."
                    ),
                    entity_type="application",
                    entity_public_id=application.public_id,
                    metadata_json={
                        "application_public_id": application.public_id,
                        "context_type": "application",
                        "context_id": application.public_id,
                    },
                    recipient_permission="voting.cast",
                )
            await session.flush()
            await session.refresh(application)
            return self._application_to_dict(application)

    async def check_eligibility(self, *, account_name: str) -> dict:
        normalized = self._normalize_account_name(account_name)
        async with get_session() as session:
            repo = ApplicationRepository(session)
            blacklist_repo = BlacklistRepository(session)
            history_rows = await repo.list_account_history(account_name=normalized, limit=10)
            history = self._eligibility_history_to_dict(history_rows)
            blacklist_entry = await blacklist_repo.find_active_by_account_name(normalized)
            if blacklist_entry is not None:
                return self._eligibility_response(
                    allowed=False,
                    status="blocked_blacklist",
                    wait_until=None,
                    reasons=[f"BLACKLIST_ACTIVE_LEVEL_{blacklist_entry.blacklist_level}"],
                    application_history=history,
                )

            pending_application = next(
                (
                    application
                    for application, _decision in history_rows
                    if str(application.status or "").lower() in self.PENDING_APPLICATION_STATUSES
                ),
                None,
            )
            if pending_application is not None:
                return self._eligibility_response(
                    allowed=False,
                    status="pending_review",
                    wait_until=None,
                    reasons=["APPLICATION_ALREADY_PENDING"],
                    application_history=history,
                )

            row = await repo.get_eligibility_by_account(normalized)
            if row is None:
                return self._eligibility_response(
                    allowed=True,
                    status="allowed",
                    wait_until=None,
                    reasons=[],
                    application_history=history,
                )

            status = row.eligibility_status
            wait_until = row.wait_until
            now = datetime.now(timezone.utc)

            if status == "cooldown" and wait_until and wait_until <= now:
                row = await repo.upsert_eligibility(
                    account_name=normalized,
                    eligibility_status="allowed",
                    wait_until=None,
                    source="decision_policy",
                    source_ref_id=None,
                    player_id=row.player_id,
                )
                status = row.eligibility_status
                wait_until = row.wait_until

            if status == "allowed":
                return self._eligibility_response(
                    allowed=True,
                    status="allowed",
                    wait_until=None,
                    reasons=[],
                    application_history=history,
                )
            if status == "cooldown":
                return self._eligibility_response(
                    allowed=False,
                    status="cooldown",
                    wait_until=wait_until,
                    reasons=["DENIAL_COOLDOWN_ACTIVE"],
                    application_history=history,
                )
            if status == "blocked_blacklist":
                return self._eligibility_response(
                    allowed=False,
                    status="blocked_blacklist",
                    wait_until=None,
                    reasons=["BLACKLIST_ACTIVE"],
                    application_history=history,
                )
            return self._eligibility_response(
                allowed=False,
                status="blocked_permanent",
                wait_until=None,
                reasons=["PERMANENT_BLOCK"],
                application_history=history,
            )

    async def list_applications(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        async with get_session() as session:
            repo = ApplicationRepository(session)
            rows = await repo.list_applications(status=status, limit=limit, offset=offset)
            return [self._application_to_dict(row) for row in rows]

    async def get_application(self, *, public_id: str) -> dict:
        async with get_session() as session:
            repo = ApplicationRepository(session)
            row = await repo.get_by_public_id(public_id)
            if row is None:
                raise ApiException(
                    status_code=404,
                    error_code="APPLICATION_NOT_FOUND",
                    message=f"Application {public_id} not found",
                )
            return self._application_to_dict(row)

    async def decide_application(
        self,
        *,
        public_id: str,
        reviewer_user_id: int,
        decision: str,
        decision_reason: str,
        reapply_policy: str,
        cooldown_days: int | None,
    ) -> dict:
        decision_value = decision.lower().strip()
        if decision_value not in {"accepted", "declined"}:
            raise ApiException(
                status_code=422,
                error_code="INVALID_DECISION",
                message="Decision must be accepted or declined",
            )

        policy_value = reapply_policy.lower().strip()
        if policy_value not in {"allow_immediate", "cooldown", "permanent_block"}:
            raise ApiException(
                status_code=422,
                error_code="INVALID_REAPPLY_POLICY",
                message="Invalid reapply policy",
            )

        policies = await self.get_policies()
        if decision_value == "accepted":
            policy_value = "allow_immediate"
            cooldown_days = None

        reapply_allowed_at: datetime | None = None
        eligibility_status = "allowed"
        if policy_value == "cooldown":
            applied_cooldown_days = cooldown_days or policies["default_cooldown_days"]
            reapply_allowed_at = datetime.now(timezone.utc) + timedelta(days=applied_cooldown_days)
            cooldown_days = applied_cooldown_days
            eligibility_status = "cooldown"
        elif policy_value == "permanent_block":
            cooldown_days = None
            eligibility_status = "blocked_permanent"
        else:
            cooldown_days = None
            eligibility_status = "allowed"

        async with get_session() as session:
            repo = ApplicationRepository(session)
            voting_repo = VotingRepository(session)
            application = await repo.get_by_public_id(public_id)
            if application is None:
                raise ApiException(
                    status_code=404,
                    error_code="APPLICATION_NOT_FOUND",
                    message=f"Application {public_id} not found",
                )
            if application.status in {"accepted", "declined"}:
                raise ApiException(
                    status_code=409,
                    error_code="APPLICATION_ALREADY_DECIDED",
                    message=f"Application {public_id} is already finalized",
                )

            application.status = decision_value
            await repo.add_decision(
                application_id=application.id,
                reviewer_user_id=reviewer_user_id,
                decision=decision_value,
                decision_reason=decision_reason,
                reapply_policy=policy_value,
                cooldown_days=cooldown_days,
                reapply_allowed_at=reapply_allowed_at,
            )

            await repo.upsert_eligibility(
                account_name=application.account_name,
                eligibility_status=eligibility_status,
                wait_until=reapply_allowed_at,
                source="decision_policy",
                source_ref_id=application.public_id,
                player_id=application.player_id,
            )

            voting_context = await voting_repo.get_context(
                context_type="application",
                context_id=application.public_id,
            )
            if voting_context is not None:
                voting_context.status = "closed"
                voting_context.closed_by_user_id = reviewer_user_id
                voting_context.closed_at = datetime.now(timezone.utc)
                voting_context.close_reason = f"application_{decision_value}"
                await voting_repo.append_event(
                    voting_context_id=voting_context.id,
                    event_type="application_decision_finalized",
                    actor_user_id=reviewer_user_id,
                    target_user_id=None,
                    vote_choice=None,
                    reason=decision_reason,
                    metadata_json={
                        "decision": decision_value,
                        "reapply_policy": policy_value,
                        "cooldown_days": cooldown_days,
                        "reapply_allowed_at": reapply_allowed_at.isoformat()
                        if reapply_allowed_at
                        else None,
                    },
                )

            await session.flush()
            await session.refresh(application)
            return self._application_to_dict(application)

    async def _resolve_voting_auto_close_days(self, repo: ConfigRegistryRepository) -> int:
        row = await repo.get_by_key(self.VOTING_AUTO_CLOSE_DAYS_CONFIG_KEY)
        if row and isinstance(row.value_json, int):
            return max(1, min(30, row.value_json))
        return self.DEFAULT_VOTING_AUTO_CLOSE_DAYS

    async def get_policies(self) -> dict[str, int | bool | str]:
        async with get_session() as session:
            config_repo = ConfigRegistryRepository(session)
            cooldown_row = await config_repo.get_by_key(self.COOLDOWN_CONFIG_KEY)
            guest_rate_row = await config_repo.get_by_key(self.GUEST_RATE_LIMIT_CONFIG_KEY)
            captcha_enabled_row = await config_repo.get_by_key(self.CAPTCHA_ENABLED_CONFIG_KEY)
            captcha_site_key_row = await config_repo.get_by_key(self.CAPTCHA_SITE_KEY_CONFIG_KEY)

        default_cooldown_days = self.DEFAULT_COOLDOWN_DAYS
        if cooldown_row and isinstance(cooldown_row.value_json, int):
            default_cooldown_days = max(1, min(365, cooldown_row.value_json))

        guest_limit = self.DEFAULT_GUEST_LIMIT_PER_24H
        if guest_rate_row and isinstance(guest_rate_row.value_json, int):
            guest_limit = max(1, min(100, guest_rate_row.value_json))

        captcha_enabled = self.DEFAULT_CAPTCHA_ENABLED
        if captcha_enabled_row and isinstance(captcha_enabled_row.value_json, bool):
            captcha_enabled = captcha_enabled_row.value_json

        captcha_site_key = self.DEFAULT_CAPTCHA_SITE_KEY
        if captcha_site_key_row and isinstance(captcha_site_key_row.value_json, str):
            captcha_site_key = captcha_site_key_row.value_json.strip()

        return {
            "default_cooldown_days": default_cooldown_days,
            "guest_max_submissions_per_24h": guest_limit,
            "captcha_enabled": captcha_enabled,
            "captcha_site_key": captcha_site_key,
        }

    async def update_policies(
        self,
        *,
        actor_user_id: int,
        default_cooldown_days: int | None,
        guest_max_submissions_per_24h: int | None,
        captcha_enabled: bool | None,
        captcha_site_key: str | None,
    ) -> dict[str, int | bool | str]:
        async with get_session() as session:
            repo = ConfigRegistryRepository(session)

            if default_cooldown_days is not None:
                if default_cooldown_days < 1 or default_cooldown_days > 365:
                    raise ApiException(
                        status_code=422,
                        error_code="INVALID_COOLDOWN_DAYS",
                        message="default_cooldown_days must be in [1, 365]",
                    )
                current = await repo.get_by_key(self.COOLDOWN_CONFIG_KEY)
                before = current.value_json if current else None
                await repo.upsert(
                    key=self.COOLDOWN_CONFIG_KEY,
                    value_json=default_cooldown_days,
                    schema_version=1,
                    is_sensitive=False,
                    updated_by_user_id=actor_user_id,
                )
                await repo.add_change(
                    config_key=self.COOLDOWN_CONFIG_KEY,
                    before_json=before,
                    after_json=default_cooldown_days,
                    schema_version=1,
                    is_sensitive=False,
                    changed_by_user_id=actor_user_id,
                    change_reason="Updated application default cooldown policy",
                    requires_approval=False,
                    status="applied",
                )

            if guest_max_submissions_per_24h is not None:
                if guest_max_submissions_per_24h < 1 or guest_max_submissions_per_24h > 100:
                    raise ApiException(
                        status_code=422,
                        error_code="INVALID_GUEST_RATE_LIMIT",
                        message="guest_max_submissions_per_24h must be in [1, 100]",
                    )
                current = await repo.get_by_key(self.GUEST_RATE_LIMIT_CONFIG_KEY)
                before = current.value_json if current else None
                await repo.upsert(
                    key=self.GUEST_RATE_LIMIT_CONFIG_KEY,
                    value_json=guest_max_submissions_per_24h,
                    schema_version=1,
                    is_sensitive=False,
                    updated_by_user_id=actor_user_id,
                )
                await repo.add_change(
                    config_key=self.GUEST_RATE_LIMIT_CONFIG_KEY,
                    before_json=before,
                    after_json=guest_max_submissions_per_24h,
                    schema_version=1,
                    is_sensitive=False,
                    changed_by_user_id=actor_user_id,
                    change_reason="Updated application guest submission rate limit policy",
                    requires_approval=False,
                    status="applied",
                )

            if captcha_enabled is not None:
                current = await repo.get_by_key(self.CAPTCHA_ENABLED_CONFIG_KEY)
                before = current.value_json if current else None
                await repo.upsert(
                    key=self.CAPTCHA_ENABLED_CONFIG_KEY,
                    value_json=bool(captcha_enabled),
                    schema_version=1,
                    is_sensitive=False,
                    updated_by_user_id=actor_user_id,
                )
                await repo.add_change(
                    config_key=self.CAPTCHA_ENABLED_CONFIG_KEY,
                    before_json=before,
                    after_json=bool(captcha_enabled),
                    schema_version=1,
                    is_sensitive=False,
                    changed_by_user_id=actor_user_id,
                    change_reason="Updated application captcha enabled policy",
                    requires_approval=False,
                    status="applied",
                )

            if captcha_site_key is not None:
                normalized_site_key = captcha_site_key.strip()
                if len(normalized_site_key) > 1024:
                    raise ApiException(
                        status_code=422,
                        error_code="INVALID_CAPTCHA_SITE_KEY",
                        message="captcha_site_key must be <= 1024 chars",
                    )
                current = await repo.get_by_key(self.CAPTCHA_SITE_KEY_CONFIG_KEY)
                before = current.value_json if current else None
                await repo.upsert(
                    key=self.CAPTCHA_SITE_KEY_CONFIG_KEY,
                    value_json=normalized_site_key,
                    schema_version=1,
                    is_sensitive=False,
                    updated_by_user_id=actor_user_id,
                )
                await repo.add_change(
                    config_key=self.CAPTCHA_SITE_KEY_CONFIG_KEY,
                    before_json=before,
                    after_json=normalized_site_key,
                    schema_version=1,
                    is_sensitive=False,
                    changed_by_user_id=actor_user_id,
                    change_reason="Updated application captcha site key",
                    requires_approval=False,
                    status="applied",
                )

        return await self.get_policies()

    async def _verify_captcha_token(
        self,
        *,
        captcha_token: str | None,
        ip_address: str | None,
    ) -> None:
        if not captcha_token or not captcha_token.strip():
            raise ApiException(
                status_code=422,
                error_code="CAPTCHA_TOKEN_REQUIRED",
                message="captcha_token is required for guest submissions",
            )
        if not self.settings.BACKEND_CAPTCHA_SECRET:
            raise ApiException(
                status_code=500,
                error_code="CAPTCHA_SECRET_NOT_CONFIGURED",
                message="Captcha secret is not configured on the server",
            )
        payload = {
            "secret": self.settings.BACKEND_CAPTCHA_SECRET,
            "response": captcha_token.strip(),
        }
        if ip_address:
            payload["remoteip"] = ip_address
        verify_url = self._resolve_captcha_verify_url()

        try:
            async with httpx.AsyncClient(
                timeout=float(self.settings.BACKEND_CAPTCHA_VERIFY_TIMEOUT_SECONDS)
            ) as client:
                response = await client.post(
                    verify_url,
                    data=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ApiException(
                status_code=502,
                error_code="CAPTCHA_PROVIDER_UNAVAILABLE",
                message="Captcha verification request failed",
            ) from exc

        if not bool(data.get("success")):
            raise ApiException(
                status_code=422,
                error_code="CAPTCHA_VERIFICATION_FAILED",
                message="Captcha verification failed",
                details={"error_codes": data.get("error-codes", [])},
            )

        provider = self.settings.BACKEND_CAPTCHA_PROVIDER.strip().lower()
        if provider in {"google_recaptcha_v3", "recaptcha_v3", "google"}:
            score = data.get("score")
            if not isinstance(score, (int, float)):
                raise ApiException(
                    status_code=422,
                    error_code="CAPTCHA_SCORE_MISSING",
                    message="Captcha provider response did not include a score",
                )
            if float(score) < float(self.settings.BACKEND_CAPTCHA_MIN_SCORE):
                raise ApiException(
                    status_code=422,
                    error_code="CAPTCHA_SCORE_TOO_LOW",
                    message="Captcha score is below configured threshold",
                    details={
                        "score": float(score),
                        "min_score": float(self.settings.BACKEND_CAPTCHA_MIN_SCORE),
                    },
                )
            expected_action = self.settings.BACKEND_CAPTCHA_EXPECTED_ACTION.strip()
            action = str(data.get("action") or "").strip()
            if expected_action:
                if not action:
                    raise ApiException(
                        status_code=422,
                        error_code="CAPTCHA_ACTION_MISSING",
                        message="Captcha action is missing in provider response",
                        details={"expected_action": expected_action},
                    )
                if action != expected_action:
                    raise ApiException(
                        status_code=422,
                        error_code="CAPTCHA_ACTION_MISMATCH",
                        message="Captcha action does not match expected action",
                        details={"expected_action": expected_action, "action": action},
                    )

    def _resolve_captcha_verify_url(self) -> str:
        raw_url = str(self.settings.BACKEND_CAPTCHA_VERIFY_URL or "").strip()
        if not raw_url:
            raise ApiException(
                status_code=500,
                error_code="CAPTCHA_VERIFY_URL_NOT_CONFIGURED",
                message="Captcha verify URL is not configured on the server",
            )

        parsed = urlparse(raw_url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return raw_url

        # Accept env values like `www.google.com/recaptcha/api/siteverify` by normalizing scheme.
        if not parsed.scheme and parsed.path and "." in parsed.path:
            normalized = f"https://{parsed.path.lstrip('/')}"
            reparsed = urlparse(normalized)
            if reparsed.scheme in {"http", "https"} and reparsed.netloc:
                return normalized

        raise ApiException(
            status_code=500,
            error_code="CAPTCHA_VERIFY_URL_INVALID",
            message="Captcha verify URL must start with http:// or https://",
            details={"configured_value": raw_url},
        )

    @staticmethod
    def _application_to_dict(row) -> dict:
        return {
            "public_id": row.public_id,
            "status": row.status,
            "submitted_at": row.submitted_at,
            "applicant_discord_id": row.applicant_discord_id,
            "submitter_type": row.submitter_type,
            "in_game_nickname": row.in_game_nickname,
            "account_name": row.account_name,
            "mta_serial": row.mta_serial,
            "english_skill": row.english_skill,
            "has_second_account": row.has_second_account,
            "second_account_name": row.second_account_name,
            "cit_journey": row.cit_journey,
            "former_groups_reason": row.former_groups_reason,
            "why_join": row.why_join,
            "punishlog_url": row.punishlog_url,
            "stats_url": row.stats_url,
            "history_url": row.history_url,
        }

    @staticmethod
    def _normalize_account_name(account_name: str) -> str:
        normalized = account_name.strip().lower()
        if not normalized:
            raise ApiException(
                status_code=422,
                error_code="ACCOUNT_NAME_INVALID",
                message="account_name cannot be empty",
            )
        return normalized

    @staticmethod
    def _eligibility_response(
        *,
        allowed: bool,
        status: str,
        wait_until: datetime | None,
        reasons: list[str],
        application_history: list[dict],
    ) -> dict:
        return {
            "allowed": allowed,
            "status": status,
            "wait_until": wait_until,
            "permanent_block": status == "blocked_permanent",
            "reasons": reasons,
            "application_history": application_history,
        }

    @staticmethod
    def _eligibility_history_to_dict(rows) -> list[dict]:
        history: list[dict] = []
        for application, decision in rows:
            history.append(
                {
                    "public_id": application.public_id,
                    "status": application.status,
                    "submitted_at": application.submitted_at,
                    "decision": decision.decision if decision is not None else None,
                    "decision_reason": (
                        decision.decision_reason if decision is not None else None
                    ),
                    "reviewed_at": decision.created_at if decision is not None else None,
                }
            )
        return history

    @staticmethod
    def _hash_ip(ip_address: str) -> str:
        return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()

    @staticmethod
    def _generate_public_id() -> str:
        return f"APP-{uuid4().hex[:12].upper()}"
