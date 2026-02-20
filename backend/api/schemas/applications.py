from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApplicationResponse(BaseModel):
    public_id: str
    status: str
    submitted_at: datetime
    applicant_discord_id: int | None = None
    submitter_type: str
    in_game_nickname: str
    account_name: str
    mta_serial: str
    english_skill: int
    has_second_account: bool
    second_account_name: str | None = None
    cit_journey: str
    former_groups_reason: str
    why_join: str
    punishlog_url: str
    stats_url: str
    history_url: str


class ApplicationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(accepted|declined)$")
    decision_reason: str = Field(min_length=3)
    reapply_policy: str = Field(
        default="allow_immediate",
        pattern="^(allow_immediate|cooldown|permanent_block)$",
    )
    cooldown_days: int | None = Field(default=None, ge=1, le=365)


class ApplicationEligibilityResponse(BaseModel):
    class ApplicationHistoryItem(BaseModel):
        public_id: str
        status: str
        submitted_at: datetime
        decision: str | None = None
        decision_reason: str | None = None
        reviewed_at: datetime | None = None

    allowed: bool
    status: str
    wait_until: datetime | None = None
    permanent_block: bool
    reasons: list[str]
    application_history: list[ApplicationHistoryItem] = Field(default_factory=list)


class ApplicationPoliciesResponse(BaseModel):
    default_cooldown_days: int
    guest_max_submissions_per_24h: int
    captcha_enabled: bool
    captcha_site_key: str


class ApplicationPoliciesUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_cooldown_days: int | None = Field(default=None, ge=1, le=365)
    guest_max_submissions_per_24h: int | None = Field(default=None, ge=1, le=100)
    captcha_enabled: bool | None = None
    captcha_site_key: str | None = Field(default=None, max_length=1024)
