import httpx
import pytest
import pytest_asyncio

from app.exceptions.network import NetworkConnectionError, NetworkTimeout
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
