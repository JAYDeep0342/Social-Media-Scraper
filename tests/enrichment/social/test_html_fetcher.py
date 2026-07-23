import httpx
import pytest
import pytest_asyncio

from app.enrichment.social.html_fetcher import WebsiteHTMLFetcher
from app.network.session_manager import SessionManager


@pytest_asyncio.fixture(autouse=True)
async def _reset_singleton():
    await SessionManager.reset_instance()
    yield
    await SessionManager.reset_instance()


@pytest.mark.asyncio
async def test_fetch_returns_html_on_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>hello</html>")

    session = SessionManager.get_instance(transport=httpx.MockTransport(handler))
    await session.startup()

    fetcher = WebsiteHTMLFetcher(session_manager=session)
    html = await fetcher.fetch("https://example.test")

    assert html == "<html>hello</html>"


@pytest.mark.asyncio
async def test_fetch_returns_none_on_4xx_5xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    session = SessionManager.get_instance(transport=httpx.MockTransport(handler))
    await session.startup()

    fetcher = WebsiteHTMLFetcher(session_manager=session)
    html = await fetcher.fetch("https://example.test")

    assert html is None


@pytest.mark.asyncio
async def test_fetch_returns_none_on_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    from app.exceptions.network import NetworkConnectionError, NetworkTimeout
    from app.network.retry_strategy import RetryPolicy

    fast_policy = RetryPolicy(
        max_attempts=2, base_delay=0.01, max_delay=0.02, jitter=0.0,
        retryable_exceptions=(NetworkConnectionError, NetworkTimeout),
    )
    session = SessionManager.get_instance(transport=httpx.MockTransport(handler), retry_policy=fast_policy)
    await session.startup()

    fetcher = WebsiteHTMLFetcher(session_manager=session)
    html = await fetcher.fetch("https://example.test")

    assert html is None
