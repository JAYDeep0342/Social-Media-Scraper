import asyncio

import pytest

from app.exceptions.network import CircuitOpen
from app.network.circuit_breaker import CircuitBreaker, CircuitState


async def _failing_call():
    raise RuntimeError("boom")


async def _succeeding_call():
    return "ok"


@pytest.mark.asyncio
async def test_starts_closed() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout_seconds=1)
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_opens_after_failure_threshold() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout_seconds=10)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(_failing_call)

    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_open_circuit_rejects_calls_immediately() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_seconds=10)

    with pytest.raises(RuntimeError):
        await breaker.call(_failing_call)
    assert breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitOpen):
        await breaker.call(_succeeding_call)


@pytest.mark.asyncio
async def test_transitions_to_half_open_after_recovery_timeout_and_closes_on_success() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_seconds=0.05, half_open_max_calls=1)

    with pytest.raises(RuntimeError):
        await breaker.call(_failing_call)
    assert breaker.state == CircuitState.OPEN

    await asyncio.sleep(0.1)

    result = await breaker.call(_succeeding_call)
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_failure_reopens_circuit() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_seconds=0.05, half_open_max_calls=1)

    with pytest.raises(RuntimeError):
        await breaker.call(_failing_call)
    await asyncio.sleep(0.1)

    with pytest.raises(RuntimeError):
        await breaker.call(_failing_call)

    assert breaker.state == CircuitState.OPEN
