"""Async token-bucket rate limiter. A generic concurrency-control primitive
with no awareness of what is being rate limited."""

import asyncio
import time
from typing import Optional

from app.config.settings import get_settings


class RateLimiter:
    def __init__(self, *, requests_per_second: Optional[float] = None, burst: Optional[int] = None) -> None:
        settings = get_settings()
        self._rate = requests_per_second or settings.RATE_LIMIT_REQUESTS_PER_SECOND
        self._capacity = float(burst or settings.RATE_LIMIT_BURST)
        self._tokens = self._capacity
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._updated_at
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._updated_at = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return

                deficit = tokens - self._tokens
                wait_time = deficit / self._rate

            await asyncio.sleep(wait_time)

    async def __aenter__(self) -> "RateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None
