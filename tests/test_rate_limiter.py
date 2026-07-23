import time

import pytest

from app.network.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_burst_capacity_is_immediate() -> None:
    limiter = RateLimiter(requests_per_second=5, burst=3)

    start = time.monotonic()
    for _ in range(3):
        await limiter.acquire()
    elapsed = time.monotonic() - start

    assert elapsed < 0.05


@pytest.mark.asyncio
async def test_exceeding_burst_forces_a_wait() -> None:
    limiter = RateLimiter(requests_per_second=10, burst=1)

    await limiter.acquire()  # consumes the only token
    start = time.monotonic()
    await limiter.acquire()  # must wait ~1/10s for a token to refill
    elapsed = time.monotonic() - start

    assert elapsed >= 0.08


@pytest.mark.asyncio
async def test_async_context_manager_acquires_a_token() -> None:
    limiter = RateLimiter(requests_per_second=5, burst=1)
    async with limiter:
        pass
    # second immediate use should now have to wait for refill
    start = time.monotonic()
    async with limiter:
        pass
    assert time.monotonic() - start >= 0.15
