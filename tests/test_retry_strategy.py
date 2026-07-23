import pytest

from app.exceptions.network import RetryExceeded
from app.network.retry_strategy import RetryPolicy


@pytest.mark.asyncio
async def test_execute_succeeds_on_first_attempt() -> None:
    calls = 0

    async def op():
        nonlocal calls
        calls += 1
        return "ok"

    policy = RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.02, jitter=0.0)
    assert await policy.execute(op) == "ok"
    assert calls == 1


@pytest.mark.asyncio
async def test_execute_retries_then_succeeds() -> None:
    calls = 0

    async def op():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("transient")
        return "ok"

    policy = RetryPolicy(max_attempts=5, base_delay=0.01, max_delay=0.02, jitter=0.0)
    assert await policy.execute(op) == "ok"
    assert calls == 3


@pytest.mark.asyncio
async def test_execute_raises_retry_exceeded_after_max_attempts() -> None:
    calls = 0

    async def op():
        nonlocal calls
        calls += 1
        raise ValueError("always fails")

    policy = RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.02, jitter=0.0)
    with pytest.raises(RetryExceeded):
        await policy.execute(op)
    assert calls == 3


@pytest.mark.asyncio
async def test_on_retry_callback_invoked_per_retry() -> None:
    retry_attempts = []

    async def op():
        raise ValueError("fails")

    async def on_retry(attempt, exc):
        retry_attempts.append(attempt)

    policy = RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.02, jitter=0.0)
    with pytest.raises(RetryExceeded):
        await policy.execute(op, on_retry=on_retry)
    assert retry_attempts == [1, 2]


def test_compute_delay_is_bounded_by_max_delay_plus_jitter() -> None:
    policy = RetryPolicy(max_attempts=10, base_delay=1.0, max_delay=2.0, jitter=0.5)
    for attempt in range(1, 8):
        delay = policy.compute_delay(attempt)
        assert 0 <= delay <= 2.5


def test_only_retryable_exceptions_are_caught() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay=0.01, retryable_exceptions=(ValueError,))

    async def op():
        raise TypeError("not retryable")

    import asyncio

    async def run():
        with pytest.raises(TypeError):
            await policy.execute(op)

    asyncio.run(run())
