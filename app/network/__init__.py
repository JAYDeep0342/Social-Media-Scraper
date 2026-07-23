"""High-performance async networking layer: shared HTTP client, session
lifecycle, retry/circuit-breaker/rate-limiter primitives, DNS cache, user
agent rotation, request/response hooks, and network metrics. Pure
infrastructure — no scraping or business logic lives here.
"""

from app.network.circuit_breaker import CircuitBreaker, CircuitState
from app.network.dns_cache import DNSCache
from app.network.http_client import HTTPClientManager
from app.network.network_metrics import NetworkMetrics, NetworkMetricsSnapshot
from app.network.rate_limiter import RateLimiter
from app.network.retry_strategy import RetryPolicy, default_retry_policy
from app.network.session_manager import SessionManager
from app.network.user_agent import UserAgentManager

__all__ = [
    "HTTPClientManager",
    "SessionManager",
    "RetryPolicy",
    "default_retry_policy",
    "CircuitBreaker",
    "CircuitState",
    "RateLimiter",
    "UserAgentManager",
    "DNSCache",
    "NetworkMetrics",
    "NetworkMetricsSnapshot",
]
