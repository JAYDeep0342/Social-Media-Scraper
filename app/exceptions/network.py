"""Networking-specific domain exceptions, extending app.exceptions.base."""

from app.exceptions.base import AppException


class NetworkConnectionError(AppException):
    """Raised when the underlying transport fails to connect or completes
    with a transport-level error.

    Named `NetworkConnectionError` rather than `ConnectionError` to avoid
    shadowing Python's builtin `ConnectionError` (same reasoning as
    `ScraperTimeoutError` in app.exceptions.errors).
    """

    status_code = 502


class RetryExceeded(AppException):
    """Raised when a retryable operation exhausts its configured attempts."""

    status_code = 502


class CircuitOpen(AppException):
    """Raised when a circuit breaker rejects a call because it is open."""

    status_code = 503


class NetworkTimeout(AppException):
    """Raised when a network operation exceeds its timeout budget."""

    status_code = 504


class DNSFailure(AppException):
    """Raised when hostname resolution fails."""

    status_code = 502
