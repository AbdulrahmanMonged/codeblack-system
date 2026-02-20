from typing import Any


class ConfigGuardrails:
    """Domain-level validation for dashboard-managed configuration keys."""

    @staticmethod
    def validate(*, key: str, value_json: Any) -> dict[str, Any]:
        normalized = value_json
        issues: list[str] = []

        if key == "bot.command_ack_timeout_seconds":
            if not isinstance(value_json, int) or value_json < 1 or value_json > 30:
                issues.append("bot.command_ack_timeout_seconds must be an int in [1, 30]")
        elif key == "voting.auto_close_days":
            if not isinstance(value_json, int) or value_json < 1 or value_json > 30:
                issues.append("voting.auto_close_days must be an int in [1, 30]")
        elif key.endswith("_channel_id"):
            if not isinstance(value_json, int) or value_json <= 0:
                issues.append(f"{key} must be a positive integer Discord channel ID")
        elif key.endswith("_role_id"):
            if not isinstance(value_json, int) or value_json <= 0:
                issues.append(f"{key} must be a positive integer Discord role ID")
        elif key.endswith("_enabled"):
            if not isinstance(value_json, bool):
                issues.append(f"{key} must be a boolean")
        elif key == "applications.default_denial_cooldown_days":
            if not isinstance(value_json, int) or value_json < 1 or value_json > 365:
                issues.append("applications.default_denial_cooldown_days must be int in [1, 365]")
        elif key == "applications.guest_max_submissions_per_24h":
            if not isinstance(value_json, int) or value_json < 1 or value_json > 100:
                issues.append("applications.guest_max_submissions_per_24h must be int in [1, 100]")
        elif key == "applications.captcha_enabled":
            if not isinstance(value_json, bool):
                issues.append("applications.captcha_enabled must be boolean")
        elif key == "applications.captcha_site_key":
            if not isinstance(value_json, str):
                issues.append("applications.captcha_site_key must be string")
            elif len(value_json.strip()) > 1024:
                issues.append("applications.captcha_site_key must be <= 1024 chars")
        elif key == "vacations.max_duration_days":
            if not isinstance(value_json, int) or value_json < 1 or value_json > 30:
                issues.append("vacations.max_duration_days must be int in [1, 30]")
        elif key == "activities.publish_queue_enabled":
            if not isinstance(value_json, bool):
                issues.append("activities.publish_queue_enabled must be boolean")
        elif key == "activities.publish_batch_limit":
            if not isinstance(value_json, int) or value_json < 1 or value_json > 200:
                issues.append("activities.publish_batch_limit must be int in [1, 200]")
        elif key == "activities.publish_retry_delay_seconds":
            if not isinstance(value_json, int) or value_json < 5 or value_json > 86400:
                issues.append("activities.publish_retry_delay_seconds must be int in [5, 86400]")
        elif key == "activities.publish_max_attempts":
            if not isinstance(value_json, int) or value_json < 1 or value_json > 50:
                issues.append("activities.publish_max_attempts must be int in [1, 50]")
        elif key == "bot.channels":
            if not isinstance(value_json, dict):
                issues.append("bot.channels must be an object")
            else:
                for channel_key, channel_value in value_json.items():
                    if channel_value is None:
                        continue
                    if not isinstance(channel_value, int) or channel_value <= 0:
                        issues.append(
                            f"bot.channels.{channel_key} must be null or a positive integer"
                        )
        elif key == "bot.features":
            if not isinstance(value_json, dict):
                issues.append("bot.features must be an object")
            else:
                for feature_key, feature_value in value_json.items():
                    if not isinstance(feature_value, bool):
                        issues.append(f"bot.features.{feature_key} must be boolean")

        return {"normalized_value": normalized, "issues": issues}

