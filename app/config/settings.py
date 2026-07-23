"""Environment-driven application settings.

All values here can be overridden via a `.env` file or real environment
variables (see `.env.example`). `get_settings()` is cached so the rest of the
app shares a single validated Settings instance.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.constants import (
    API_V1_PREFIX,
    APP_TITLE,
    DEFAULT_TIMEOUT,
    MAX_CONCURRENCY,
    MAX_HTTP_CONNECTIONS,
    MAX_RETRIES,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App metadata ---
    APP_NAME: str = APP_TITLE
    APP_VERSION: str = "0.1.0"
    ENV: str = Field(default="development", description="development | staging | production")
    DEBUG: bool = Field(default=True)

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = API_V1_PREFIX

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FILE_NAME: str = "app.log"
    LOG_MAX_BYTES: int = 5 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5

    # --- Concurrency / performance ---
    MAX_CONCURRENCY: int = Field(
        default=MAX_CONCURRENCY, ge=1, description="Global semaphore limit for concurrent async tasks"
    )

    # --- HTTP client tuning (placeholders for the future async client) ---
    REQUEST_TIMEOUT_SECONDS: float = Field(default=DEFAULT_TIMEOUT, gt=0)
    CONNECT_TIMEOUT_SECONDS: float = Field(default=5.0, gt=0)
    MAX_RETRIES: int = Field(default=MAX_RETRIES, ge=0)
    RETRY_BACKOFF_BASE: float = Field(default=0.5, ge=0)
    CONNECTION_POOL_SIZE: int = Field(default=MAX_HTTP_CONNECTIONS, ge=1)
    CONNECTION_POOL_SIZE_PER_HOST: int = Field(default=20, ge=1)

    # --- Benchmarking ---
    BENCHMARK_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
