"""Singleton session manager: owns the shared HTTP client, per-host rate
limiters, per-host circuit breakers, retry policy, and network metrics for
the whole process. Provides automatic startup/shutdown and a single
`request()` entry point that composes all of them around one HTTP call.

    session = SessionManager.get_instance()
    await session.startup()
    response = await session.request("GET", "https://example.com")
    await session.shutdown()

`app.core.lifespan` calls startup()/shutdown() automatically as part of the
FastAPI application lifecycle.

Rate limiting and circuit breaking are keyed per-host (see `_host_for`), so
one failing/slow host (e.g. a dead business website) can never throttle or
trip the breaker for an unrelated host (e.g. DuckDuckGo, or another
business's site) -- each hostname gets its own independent RateLimiter and
CircuitBreaker, created lazily on first use. The retry policy stays a
single shared instance: it is pure configuration (attempt count, backoff
timings) with no per-call mutable state, so sharing it across hosts is
safe and keeps retry behavior identical to before.
"""

from typing import Any, Dict, Optional

import httpx

from app.core.logging import get_logger
from app.exceptions.network import NetworkConnectionError, NetworkTimeout
from app.network.circuit_breaker import CircuitBreaker
from app.network.http_client import HTTPClientManager
from app.network.network_metrics import NetworkMetrics
from app.network.rate_limiter import RateLimiter
from app.network.request_hooks import DEFAULT_REQUEST_HOOKS
from app.network.response_hooks import DEFAULT_RESPONSE_HOOKS
from app.network.retry_strategy import RetryPolicy, default_retry_policy
from app.utils.url_helper import extract_domain

logger = get_logger(__name__)


class SessionManager:
    """Process-wide singleton. Use `SessionManager.get_instance()`."""

    _instance: Optional["SessionManager"] = None

    def __init__(
        self,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        if SessionManager._instance is not None:
            raise RuntimeError("SessionManager is a singleton; use SessionManager.get_instance()")

        self._client_manager = HTTPClientManager(
            event_hooks={"request": DEFAULT_REQUEST_HOOKS, "response": DEFAULT_RESPONSE_HOOKS},
            transport=transport,
        )
        self._rate_limiters: Dict[str, RateLimiter] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._retry_policy: RetryPolicy = retry_policy or default_retry_policy(
            retryable_exceptions=(NetworkConnectionError, NetworkTimeout)
        )
        self.metrics = NetworkMetrics()
        self._started = False

        SessionManager._instance = self

    @staticmethod
    def _host_for(url: str) -> str:
        return extract_domain(url) or "default"

    def rate_limiter_for(self, host: str) -> RateLimiter:
        """Returns the host's RateLimiter, creating it on first use. Safe to
        call from concurrent coroutines: dict get-or-create here never
        awaits between the check and the write, so there's no interleaving
        window for two coroutines to create duplicate instances for the
        same host."""
        limiter = self._rate_limiters.get(host)
        if limiter is None:
            limiter = RateLimiter()
            self._rate_limiters[host] = limiter
        return limiter

    def circuit_breaker_for(self, host: str) -> CircuitBreaker:
        """Returns the host's CircuitBreaker, creating it on first use (same
        get-or-create safety as `rate_limiter_for`)."""
        breaker = self._circuit_breakers.get(host)
        if breaker is None:
            breaker = CircuitBreaker(name=host)
            self._circuit_breakers[host] = breaker
        return breaker

    @classmethod
    def get_instance(
        cls,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> "SessionManager":
        if cls._instance is None:
            cls(transport=transport, retry_policy=retry_policy)
        return cls._instance  # type: ignore[return-value]

    @classmethod
    async def reset_instance(cls) -> None:
        """Test helper: closes and clears the singleton so the next
        get_instance() call builds a fresh session."""
        if cls._instance is not None:
            await cls._instance.shutdown()

    async def startup(self) -> None:
        self._started = True
        logger.debug("SessionManager started")

    async def shutdown(self) -> None:
        if self._started or not self._client_manager.is_closed:
            await self._client_manager.aclose()
            self._started = False
            logger.debug("SessionManager shut down")
        if SessionManager._instance is self:
            SessionManager._instance = None

    async def request(
        self, method: str, url: str, *, retry_policy: Optional[RetryPolicy] = None, **kwargs: Any
    ) -> httpx.Response:
        host = self._host_for(url)
        circuit_breaker = self.circuit_breaker_for(host)
        rate_limiter = self.rate_limiter_for(host)
        policy = retry_policy or self._retry_policy

        async def _call() -> httpx.Response:
            try:
                return await self._client_manager.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                raise NetworkTimeout(f"Request to {url} timed out") from exc
            except httpx.HTTPError as exc:
                raise NetworkConnectionError(f"Request to {url} failed") from exc

        async def _guarded_call() -> httpx.Response:
            return await circuit_breaker.call(_call)

        async def _on_retry(attempt: int, exc: BaseException) -> None:
            await self.metrics.record_retry()
            logger.debug("Retrying %s %s (attempt %d) after %s", method, url, attempt, exc)

        async def _rate_limited_call() -> httpx.Response:
            await rate_limiter.acquire()
            return await policy.execute(_guarded_call, label=f"{method} {url}", on_retry=_on_retry)

        start = await self.metrics.record_request_start()
        try:
            response = await _rate_limited_call()
        except Exception:
            await self.metrics.record_request_end(start, success=False)
            raise
        else:
            await self.metrics.record_request_end(start, success=True)
            return response

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client_manager.client
