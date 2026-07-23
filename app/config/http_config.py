"""HTTP client configuration placeholders.

This module only assembles *configuration* consumed by a future async HTTP
client (Phase 2+). It performs no network I/O.
"""

from dataclasses import dataclass, field

from app.config.constants import BASE_ACCEPTED_ENCODINGS, DEFAULT_USER_AGENTS
from app.config.settings import get_settings

_settings = get_settings()


def _accepted_encodings() -> tuple[str, ...]:
    """gzip/deflate are decoded by httpx with no extra dependencies; brotli
    ("br") is only advertised if a brotli decoder is actually installed, so
    we never advertise support we can't decode."""
    try:
        import brotli  # noqa: F401
    except ImportError:
        try:
            import brotlicffi  # noqa: F401
        except ImportError:
            return BASE_ACCEPTED_ENCODINGS
    return (*BASE_ACCEPTED_ENCODINGS, "br")


@dataclass(frozen=True, slots=True)
class HTTPClientConfig:
    timeout_seconds: float = _settings.REQUEST_TIMEOUT_SECONDS
    connect_timeout_seconds: float = _settings.CONNECT_TIMEOUT_SECONDS
    max_retries: int = _settings.MAX_RETRIES
    retry_backoff_base: float = _settings.RETRY_BACKOFF_BASE
    pool_size: int = _settings.CONNECTION_POOL_SIZE
    pool_size_per_host: int = _settings.CONNECTION_POOL_SIZE_PER_HOST
    semaphore_limit: int = _settings.MAX_CONCURRENCY
    user_agents: list[str] = field(default_factory=lambda: list(DEFAULT_USER_AGENTS))
    default_headers: dict[str, str] = field(
        default_factory=lambda: {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": ", ".join(_accepted_encodings()),
            "Connection": "keep-alive",
        }
    )

    def headers_with_user_agent(self, index: int = 0) -> dict[str, str]:
        """Merge the default headers with a rotated User-Agent value."""
        agent = self.user_agents[index % len(self.user_agents)]
        return {**self.default_headers, "User-Agent": agent}


http_config = HTTPClientConfig()
