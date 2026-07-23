"""Generic retry engine: exponential backoff + random jitter, configurable
attempt count. Framework/domain-agnostic — has no knowledge of HTTP.
"""

import asyncio
import random
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional, Tuple, Type, TypeVar

from app.config.settings import get_settings
from app.exceptions.network import RetryExceeded

T = TypeVar("T")
OnRetryCallback = Callable[[int, BaseException], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0
    jitter: float = 0.5
    retryable_exceptions: Tuple[Type[BaseException], ...] = field(default=(Exception,))

    def compute_delay(self, attempt: int) -> float:
        """Exponential backoff capped at `max_delay`, plus uniform jitter."""
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        return delay + random.uniform(0, self.jitter)

    async def execute(
        self,
        func: Callable[[], Awaitable[T]],
        *,
        label: str = "operation",
        on_retry: Optional[OnRetryCallback] = None,
    ) -> T:
        last_exc: Optional[BaseException] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await func()
            except self.retryable_exceptions as exc:
                last_exc = exc
                if attempt >= self.max_attempts:
                    break
                if on_retry is not None:
                    await on_retry(attempt, exc)
                await asyncio.sleep(self.compute_delay(attempt))

        raise RetryExceeded(
            f"{label} failed after {self.max_attempts} attempts",
            details={"last_error": str(last_exc)},
        ) from last_exc


def default_retry_policy(
    *, retryable_exceptions: Tuple[Type[BaseException], ...] = (Exception,)
) -> RetryPolicy:
    settings = get_settings()
    return RetryPolicy(
        max_attempts=settings.MAX_RETRIES + 1,  # +1: MAX_RETRIES counts retries after the first attempt
        base_delay=settings.RETRY_BACKOFF_BASE,
        max_delay=settings.RETRY_MAX_DELAY_SECONDS,
        jitter=settings.RETRY_JITTER_SECONDS,
        retryable_exceptions=retryable_exceptions,
    )
