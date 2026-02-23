from functools import lru_cache
from pathlib import Path
from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_OWNER_IDS: Final[tuple[int, ...]] = (
    757387358621532164,
    1162165557647380542,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ROOT_ENV_FILE = _PROJECT_ROOT / ".env"


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # FastAPI app
    BACKEND_APP_NAME: str = "CodeBlack Backend"
    BACKEND_APP_VERSION: str = "0.1.0"
    BACKEND_API_PREFIX: str = "/api/v1"
    BACKEND_ENV: str = "development"
    BACKEND_DEV_UNLOCK_ALL: bool = False
    BACKEND_LOG_LEVEL: str = "INFO"
    BACKEND_LOG_FORMAT: str = "text"
    BACKEND_ENABLE_ACCESS_LOG: bool = True
    BACKEND_ENABLE_METRICS: bool = True
    BACKEND_AUDIT_ENABLED: bool = True
    BACKEND_CORS_ENABLED: bool = True
    BACKEND_CORS_ALLOW_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"
    BACKEND_CORS_ALLOW_CREDENTIALS: bool = True
    BACKEND_CORS_ALLOW_METHODS: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    BACKEND_CORS_ALLOW_HEADERS: str = (
        "Authorization,Content-Type,Accept,Origin,X-Requested-With,X-CSRF-Token"
    )
    BACKEND_CORS_EXPOSE_HEADERS: str = "X-Request-ID"
    BACKEND_CORS_MAX_AGE_SECONDS: int = 600

    # Database
    BACKEND_DATABASE_URL: str = ""
    BACKEND_DATABASE_ECHO: bool = False
    BACKEND_DATABASE_POOL_SIZE: int = 10
    BACKEND_DATABASE_MAX_OVERFLOW: int = 20
    BACKEND_AUTO_CREATE_TABLES: bool = True
    BACKEND_BOOTSTRAP_BLOCKING: bool = False
    BACKEND_BOOTSTRAP_RETRY_ATTEMPTS: int = 3
    BACKEND_BOOTSTRAP_RETRY_DELAY_SECONDS: int = 2

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "REDACTED"

    # Redis / IPC
    REDIS_URL: str = "redis://localhost:6379/0"
    IPC_STREAM_PREFIX: str = "REDACTED"
    BACKEND_CACHE_ENABLED: bool = True
    BACKEND_CACHE_PREFIX: str = "REDACTED:cache"
    BACKEND_CACHE_PUBLIC_TTL_SECONDS: int = 60
    BACKEND_CACHE_AUTH_LIST_TTL_SECONDS: int = 30
    BACKEND_CACHE_NOTIFICATIONS_TTL_SECONDS: int = 15
    BACKEND_CACHE_VOTING_TTL_SECONDS: int = 10
    BACKEND_ELIGIBILITY_PRECHECK_TTL_SECONDS: int = 900

    # Runtime policy
    BOT_COMMAND_ACK_TIMEOUT_SECONDS: int = 5
    DISCORD_GUILD_ID: int | None = None
    DISCORD_BOT_TOKEN: str = ""
    DISCORD_API_BASE_URL: str = "https://discord.com/api/v10"
    DISCORD_CLIENT_ID: str = ""
    DISCORD_CLIENT_SECRET: str = ""
    DISCORD_REDIRECT_URI: str = "http://127.0.0.1:5173/auth/callback"
    DISCORD_OAUTH_SCOPES: str = "identify guilds"

    # Auth
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_MINUTES: int = 180
    JWT_LEEWAY_SECONDS: int = 30
    BACKEND_AUTH_STATE_TTL_SECONDS: int = 600
    BACKEND_AUTH_FRONTEND_SUCCESS_URL: str = ""
    BACKEND_AUTH_FRONTEND_FAILURE_URL: str = ""
    BACKEND_AUTH_COOKIE_NAME: str = "REDACTED_session"
    BACKEND_AUTH_COOKIE_PATH: str = "/"
    BACKEND_AUTH_COOKIE_DOMAIN: str = ""
    BACKEND_AUTH_COOKIE_SAMESITE: str = "lax"
    BACKEND_AUTH_COOKIE_SECURE: bool = False
    BACKEND_AUTH_COOKIE_MAX_AGE_SECONDS: int = 0

    # Celery (shared with bot)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Reliability / rate limiting
    BACKEND_IPC_MAX_RETRIES: int = 2
    BACKEND_IPC_RETRY_BACKOFF_MS: int = 300
    BACKEND_IPC_DEAD_LETTER_MAXLEN: int = 10000
    BACKEND_RATE_LIMIT_ENABLED: bool = True
    BACKEND_RATE_LIMIT_WINDOW_SECONDS: int = 60
    BACKEND_RATE_LIMIT_MAX_REQUESTS: int = 180
    BACKEND_RATE_LIMIT_PRIVILEGED_MAX_REQUESTS: int = 45
    BACKEND_RATE_LIMIT_AUTH_MAX_REQUESTS: int = 30
    BACKEND_ANOMALY_WINDOW_SECONDS: int = 300
    BACKEND_ANOMALY_THRESHOLD: int = 12

    # Bunny object storage
    BUNNY_STORAGE_ENDPOINT: str = ""
    BUNNY_STORAGE_ZONE: str = ""
    BUNNY_STORAGE_ACCESS_KEY: str = ""
    BUNNY_STORAGE_PUBLIC_BASE_URL: str = ""

    # CAPTCHA (guest applications)
    BACKEND_CAPTCHA_SECRET: str = ""
    BACKEND_CAPTCHA_PROVIDER: str = "google_recaptcha_v3"
    BACKEND_CAPTCHA_VERIFY_URL: str = "https://www.google.com/recaptcha/api/siteverify"
    BACKEND_CAPTCHA_VERIFY_TIMEOUT_SECONDS: int = 5
    BACKEND_CAPTCHA_MIN_SCORE: float = 0.5
    BACKEND_CAPTCHA_EXPECTED_ACTION: str = "application_submit"

    # Seed configuration
    BACKEND_OWNER_DISCORD_IDS: str = ",".join(str(user_id) for user_id in DEFAULT_OWNER_IDS)
    BACKEND_INITIAL_MEMBER_ROLE_ID: int = 1312800512139202732
    BLACKLIST_SUFFIX_KEY: str = "C-X"

    @property
    def database_url(self) -> str:
        if self.BACKEND_DATABASE_URL:
            return self.BACKEND_DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def owner_discord_ids(self) -> set[int]:
        ids: set[int] = set()
        for raw in self.BACKEND_OWNER_DISCORD_IDS.split(","):
            cleaned = raw.strip()
            if not cleaned:
                continue
            try:
                ids.add(int(cleaned))
            except ValueError:
                continue
        return ids

    @property
    def oauth_scopes(self) -> str:
        return " ".join(
            scope.strip() for scope in self.DISCORD_OAUTH_SCOPES.split() if scope.strip()
        )

    @property
    def auth_cookie_domain(self) -> str | None:
        cleaned = self.BACKEND_AUTH_COOKIE_DOMAIN.strip()
        return cleaned or None

    @property
    def auth_cookie_max_age_seconds(self) -> int:
        if self.BACKEND_AUTH_COOKIE_MAX_AGE_SECONDS > 0:
            return self.BACKEND_AUTH_COOKIE_MAX_AGE_SECONDS
        return self.JWT_EXP_MINUTES * 60

    @property
    def auth_cookie_samesite(self) -> str:
        normalized = self.BACKEND_AUTH_COOKIE_SAMESITE.strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            return "lax"
        if normalized == "none" and not self.BACKEND_AUTH_COOKIE_SECURE:
            return "lax"
        return normalized

    @property
    def cors_allow_origins(self) -> list[str]:
        return self._split_csv(self.BACKEND_CORS_ALLOW_ORIGINS)

    @property
    def cors_allow_methods(self) -> list[str]:
        return self._split_csv(self.BACKEND_CORS_ALLOW_METHODS)

    @property
    def cors_allow_headers(self) -> list[str]:
        return self._split_csv(self.BACKEND_CORS_ALLOW_HEADERS)

    @property
    def cors_expose_headers(self) -> list[str]:
        return self._split_csv(self.BACKEND_CORS_EXPOSE_HEADERS)

    @staticmethod
    def _split_csv(raw: str) -> list[str]:
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def is_development_environment(self) -> bool:
        return self.BACKEND_ENV.strip().lower() in {"dev", "development", "local", "test"}

    @property
    def dev_unlock_enabled(self) -> bool:
        return self.BACKEND_DEV_UNLOCK_ALL and self.is_development_environment


@lru_cache
def get_settings() -> BackendSettings:
    return BackendSettings()

