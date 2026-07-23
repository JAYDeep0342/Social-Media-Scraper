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
    BROWSER_HEADLESS,
    BROWSER_NAVIGATION_TIMEOUT_SECONDS,
    BROWSER_POOL_SIZE,
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS,
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
    CONNECT_TIMEOUT_SECONDS,
    CONNECTION_POOL_SIZE_PER_HOST,
    DEFAULT_TIMEOUT,
    DNS_CACHE_TTL_SECONDS,
    HTTP2_ENABLED,
    MAX_CONCURRENCY,
    MAX_HTTP_CONNECTIONS,
    MAX_RETRIES,
    RATE_LIMIT_BURST,
    RATE_LIMIT_REQUESTS_PER_SECOND,
    RETRY_BACKOFF_BASE,
    RETRY_JITTER_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
    SCROLL_MAX_ATTEMPTS_WITHOUT_PROGRESS,
    SCROLL_MAX_TOTAL_ATTEMPTS,
    SCROLL_PAUSE_SECONDS,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
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

    # --- HTTP client tuning ---
    REQUEST_TIMEOUT_SECONDS: float = Field(default=DEFAULT_TIMEOUT, gt=0)
    CONNECT_TIMEOUT_SECONDS: float = Field(default=CONNECT_TIMEOUT_SECONDS, gt=0)
    MAX_RETRIES: int = Field(default=MAX_RETRIES, ge=0)
    RETRY_BACKOFF_BASE: float = Field(default=RETRY_BACKOFF_BASE, ge=0)
    CONNECTION_POOL_SIZE: int = Field(default=MAX_HTTP_CONNECTIONS, ge=1)
    CONNECTION_POOL_SIZE_PER_HOST: int = Field(default=CONNECTION_POOL_SIZE_PER_HOST, ge=1)
    HTTP2_ENABLED: bool = Field(default=HTTP2_ENABLED)

    # --- Retry engine ---
    RETRY_MAX_DELAY_SECONDS: float = Field(default=RETRY_MAX_DELAY_SECONDS, ge=0)
    RETRY_JITTER_SECONDS: float = Field(default=RETRY_JITTER_SECONDS, ge=0)

    # --- Circuit breaker ---
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=CIRCUIT_BREAKER_FAILURE_THRESHOLD, ge=1)
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS: float = Field(
        default=CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS, gt=0
    )
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = Field(default=CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS, ge=1)

    # --- Rate limiter (token bucket) ---
    RATE_LIMIT_REQUESTS_PER_SECOND: float = Field(default=RATE_LIMIT_REQUESTS_PER_SECOND, gt=0)
    RATE_LIMIT_BURST: int = Field(default=RATE_LIMIT_BURST, ge=1)

    # --- DNS cache ---
    DNS_CACHE_TTL_SECONDS: float = Field(default=DNS_CACHE_TTL_SECONDS, ge=0)

    # --- Google Maps discovery: browser ---
    BROWSER_HEADLESS: bool = Field(default=BROWSER_HEADLESS)
    BROWSER_NAVIGATION_TIMEOUT_SECONDS: float = Field(default=BROWSER_NAVIGATION_TIMEOUT_SECONDS, gt=0)
    BROWSER_POOL_SIZE: int = Field(default=BROWSER_POOL_SIZE, ge=1)
    VIEWPORT_WIDTH: int = Field(default=VIEWPORT_WIDTH, ge=1)
    VIEWPORT_HEIGHT: int = Field(default=VIEWPORT_HEIGHT, ge=1)

    # --- Google Maps discovery: scrolling ---
    SCROLL_PAUSE_SECONDS: float = Field(default=SCROLL_PAUSE_SECONDS, gt=0)
    SCROLL_MAX_ATTEMPTS_WITHOUT_PROGRESS: int = Field(default=SCROLL_MAX_ATTEMPTS_WITHOUT_PROGRESS, ge=1)
    SCROLL_MAX_TOTAL_ATTEMPTS: int = Field(default=SCROLL_MAX_TOTAL_ATTEMPTS, ge=1)

    # --- Benchmarking ---
    BENCHMARK_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
