from __future__ import annotations


class BotControlGuardrails:
    CHANNEL_KEYS = (
        "live_scores_channel_id",
        "recruitment_review_channel_id",
        "orders_notification_channel_id",
        "error_report_channel_id",
    )
    FEATURE_KEYS = (
        "watch_cop_live_scores",
        "irc_bridge",
        "group_chat_watcher",
        "activity_monitor",
    )

    @classmethod
    def validate_channels(cls, payload: dict) -> list[str]:
        issues: list[str] = []
        for key, value in payload.items():
            if key not in cls.CHANNEL_KEYS:
                issues.append(f"Unknown channel key: {key}")
                continue
            if value is not None and (not isinstance(value, int) or value <= 0):
                issues.append(f"{key} must be a positive integer or null")
        return issues

    @classmethod
    def validate_features(cls, payload: dict) -> list[str]:
        issues: list[str] = []
        for key, value in payload.items():
            if key not in cls.FEATURE_KEYS:
                issues.append(f"Unknown feature key: {key}")
                continue
            if not isinstance(value, bool):
                issues.append(f"{key} must be a boolean")
        return issues
