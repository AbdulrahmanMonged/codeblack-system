from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Discord
    DISCORD_BOT_TOKEN: str

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "codeblack"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync URL for Alembic migrations."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Forum credentials
    CIT_USERNAME: str = ""
    CIT_PASSWORD: str = ""

    # Cloudflare bypass (Capsolver API - no browser needed)
    CAPSOLVER_API_KEY: str = ""
    CF_PROXY: str = ""

    # Legacy proxy (kept for IRC)
    OXYLABS_PROXY: str = ""
    IRC_PROXY: str = ""

    # IRC
    IRC_SERVER: str = "irc.cit2.net"
    IRC_PORT: int = 6667
    IRC_CHANNEL: str = "#main-echo"
    IRC_NICKNAME: str = ""
    IRC_PASSWORD: str = ""
    IRC_DISCORD_CHANNEL_ID: int = 1454484789334900846

    # Celery (uses separate Redis DBs to avoid key collisions)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # IPC
    IPC_STREAM_PREFIX: str = "codeblack"

    # GitHub (for auto-update)
    GITHUB_TOKEN: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
