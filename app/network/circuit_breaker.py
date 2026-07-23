"""Async circuit breaker: Closed -> Open -> Half-Open state machine that
protects a downstream dependency from being hammered while it's failing.

- Closed: calls pass through; failures are counted.
- Open: calls are rejected immediately (CircuitOpen) until the recovery
  timeout elapses.
- Half-Open: a limited number of trial calls are allowed through; a success
  closes the circuit again, a failure reopens it.
"""

import asyncio
import time
from enum import Enum
from typing import Awaitable, Callable, Optional, TypeVar

from app.config.settings import get_settings
from app.exceptions.network import CircuitOpen

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        *,
        name: str = "default",
        failure_threshold: Optional[int] = None,
        recovery_timeout_seconds: Optional[float] = None,
        half_open_max_calls: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.name = name
        self._failure_threshold = failure_threshold or settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self._recovery_timeout = recovery_timeout_seconds or settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS
        self._half_open_max_calls = half_open_max_calls or settings.CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float = 0.0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def _before_call(self) -> None:
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise CircuitOpen(f"Circuit '{self.name}' is open")

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._half_open_max_calls:
                    raise CircuitOpen(f"Circuit '{self.name}' is half-open and at capacity")
                self._half_open_calls += 1

    async def _on_success(self) -> None:
        async with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
            elif self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    async def call(self, func: Callable[[], Awaitable[T]]) -> T:
        await self._before_call()
        try:
            result = await func()
        except Exception:
            await self._on_failure()
            raise
        else:
            await self._on_success()
            return result
