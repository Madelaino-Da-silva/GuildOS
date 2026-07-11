"""
GuildOS application configuration.

All runtime configuration is sourced from environment variables (typically
via a `.env` file in development, or real environment variables in
production/Docker). Nothing sensitive is hard-coded.

This module is the single source of truth for configuration across the
FastAPI app, the Discord bot, and the AI services, so all three components
import `settings` from here instead of reading `os.environ` directly.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are loaded (in order of precedence) from:
      1. Real environment variables (e.g. set by Docker Compose)
      2. A `.env` file in the working directory
      3. The defaults declared below (only for genuinely non-secret values)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- General -----------------------------------------------------
    APP_NAME: str = "GuildOS"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    TIMEZONE: str = "UTC"

    # ---- Security ------------------------------------------------------
    SECRET_KEY: str = Field(..., description="Used to sign JWTs. Must be set in .env")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours
    JWT_ALGORITHM: str = "HS256"

    # ---- Database ------------------------------------------------------
    # Defaults to local SQLite; set DATABASE_URL to a postgres:// URL to
    # migrate to PostgreSQL with zero code changes (see docs/DATABASE.md).
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/guildos.db"

    # ---- Discord -------------------------------------------------------
    DISCORD_BOT_TOKEN: str = Field(..., description="Discord bot token")
    DISCORD_GUILD_ID: int = Field(..., description="The Outsiders guild's Discord server ID")
    DISCORD_APPLICATION_CHANNEL_ID: int | None = None
    DISCORD_STAFF_CHANNEL_ID: int | None = None
    DISCORD_REPORT_CHANNEL_ID: int | None = None
    DISCORD_OWNER_DM_USER_ID: int | None = None
    DISCORD_COMMAND_PREFIX: str = "!"

    # ---- OpenAI --------------------------------------------------------
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for AI features")
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_TIMEOUT_SECONDS: int = 30

    # ---- CORS / Dashboard -----------------------------------------------
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ---- Logging ---------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (avoids re-parsing env on every call)."""
    return Settings()


settings = get_settings()
