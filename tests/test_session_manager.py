import httpx
import pytest
import pytest_asyncio

from app.config.settings import get_settings
from app.exceptions.network import NetworkConnectionError, NetworkTimeout
from app.network.circuit_breaker import CircuitState
from app.network.retry_strategy import RetryPolicy
from app.network.session_manager import SessionManager

_FAST_RETRY_POLICY = RetryPolicy(
    max_attempts=2,
    base_delay=0.01,
    max_delay=0.02,
    jitter=0.0,
    retryable_exceptions=(NetworkConnectionError, NetworkTimeout),
)


def _mock_transport(status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"ok": True})

    return httpx.MockTransport(handler)


@pytest_asyncio.fixture(autouse=True)
async def _reset_singleton():
    await SessionManager.reset_instance()
    yield
    await SessionManager.reset_instance()


@pytest.mark.asyncio
async def test_get_instance_returns_the_same_singleton() -> None:
    a = SessionManager.get_instance(transport=_mock_transport())
    b = SessionManager.get_instance()
    assert a is b


@pytest.mark.asyncio
async def test_direct_construction_after_get_instance_raises() -> None:
    SessionManager.get_instance(transport=_mock_transport())
    with pytest.raises(RuntimeError):
        SessionManager()


@pytest.mark.asyncio
async def test_startup_and_shutdown_lifecycle() -> None:
    session = SessionManager.get_instance(transport=_mock_transport())
    await session.startup()
    assert not session.client.is_closed

    await session.shutdown()
    assert session.client.is_closed
    # after shutdown, the singleton is cleared so a fresh one is built next
    assert SessionManager.get_instance(transport=_mock_transport()) is not session


@pytest.mark.asyncio
async def test_request_succeeds_through_full_stack() -> None:
    session = SessionManager.get_instance(transport=_mock_transport())
    await session.startup()

    response = await session.request("GET", "https://example.test/ping")
    assert response.status_code == 200

    snapshot = await session.metrics.snapshot()
    assert snapshot.total_requests == 1
    assert snapshot.successful_requests == 1
    assert snapshot.open_connections == 0


@pytest.mark.asyncio
async def test_failed_requests_are_recorded_in_metrics() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    session = SessionManager.get_instance(transport=httpx.MockTransport(handler), retry_policy=_FAST_RETRY_POLICY)
    await session.startup()

    with pytest.raises(Exception):
        await session.request("GET", "https://example.test/ping")

    snapshot = await session.metrics.snapshot()
    assert snapshot.failed_requests == 1


@pytest.mark.asyncio
async def test_rate_limiter_is_created_per_host_and_reused() -> None:
    session = SessionManager.get_instance(transport=_mock_transport())

    a1 = session.rate_limiter_for("hosta.test")
    a2 = session.rate_limiter_for("hosta.test")
    b = session.rate_limiter_for("hostb.test")

    assert a1 is a2  # same host -> same instance, reused
    assert a1 is not b  # different host -> independent instance


@pytest.mark.asyncio
async def test_circuit_breaker_is_created_per_host_and_reused() -> None:
    session = SessionManager.get_instance(transport=_mock_transport())

    a1 = session.circuit_breaker_for("hosta.test")
    a2 = session.circuit_breaker_for("hosta.test")
    b = session.circuit_breaker_for("hostb.test")

    assert a1 is a2
    assert a1 is not b


@pytest.mark.asyncio
async def test_circuit_breaker_opening_for_one_host_does_not_affect_another() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "failing-host.test" in str(request.url):
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json={"ok": True})

    session = SessionManager.get_instance(transport=httpx.MockTransport(handler), retry_policy=_FAST_RETRY_POLICY)
    await session.startup()
    settings = get_settings()

    # Exhaust the failing host's failure threshold (each call contributes up
    # to _FAST_RETRY_POLICY.max_attempts=2 failures) to trip its breaker open.
    attempts_needed = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
    for _ in range(attempts_needed):
        with pytest.raises(Exception):
            await session.request("GET", "https://failing-host.test/ping")

    assert session.circuit_breaker_for("failing-host.test").state == CircuitState.OPEN

    # An unrelated host must be completely unaffected by the failing one.
    response = await session.request("GET", "https://healthy-host.test/ping")
    assert response.status_code == 200
    assert session.circuit_breaker_for("healthy-host.test").state == CircuitState.CLOSED
