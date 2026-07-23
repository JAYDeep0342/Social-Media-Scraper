from urllib.parse import quote

import httpx
import pytest
import pytest_asyncio

from app.exceptions.network import NetworkConnectionError, NetworkTimeout
from app.network.retry_strategy import RetryPolicy
from app.network.session_manager import SessionManager
from app.providers.duckduckgo import DuckDuckGoSearchProvider

_FAST_RETRY_POLICY = RetryPolicy(
    max_attempts=2, base_delay=0.01, max_delay=0.02, jitter=0.0, retryable_exceptions=(NetworkConnectionError, NetworkTimeout)
)


def _ddg_result_html(*targets: str) -> str:
    """Builds HTML mirroring DuckDuckGo's real html-endpoint markup
    (verified live): each organic result is an `a.result__a` whose href
    wraps the real target behind `//duckduckgo.com/l/?uddg=<encoded>`.
    """
    links = "".join(
        f'<a class="result__a" href="//duckduckgo.com/l/?uddg={quote(target, safe="")}&amp;rut=abc123">Result</a>'
        for target in targets
    )
    return f"<html><body><div id=\"links\">{links}</div></body></html>"


@pytest_asyncio.fixture(autouse=True)
async def _reset_singleton():
    await SessionManager.reset_instance()
    yield
    await SessionManager.reset_instance()


@pytest.mark.asyncio
async def test_discover_unwraps_ddg_redirects() -> None:
    html = _ddg_result_html("https://www.instagram.com/starbucks/", "https://www.instagram.com/starbucks/reels/")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    session = SessionManager.get_instance(transport=httpx.MockTransport(handler))
    await session.startup()

    provider = DuckDuckGoSearchProvider(session_manager=session)
    results = await provider.discover('site:instagram.com "Starbucks"', "", limit=10)

    assert results == ["https://www.instagram.com/starbucks/", "https://www.instagram.com/starbucks/reels/"]


@pytest.mark.asyncio
async def test_discover_respects_limit() -> None:
    html = _ddg_result_html(*[f"https://www.instagram.com/biz{i}/" for i in range(5)])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    session = SessionManager.get_instance(transport=httpx.MockTransport(handler))
    await session.startup()

    provider = DuckDuckGoSearchProvider(session_manager=session)
    results = await provider.discover("query", "", limit=2)

    assert len(results) == 2


@pytest.mark.asyncio
async def test_discover_returns_empty_list_on_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    session = SessionManager.get_instance(transport=httpx.MockTransport(handler))
    await session.startup()

    provider = DuckDuckGoSearchProvider(session_manager=session)
    results = await provider.discover("query", "", limit=10)

    assert results == []


@pytest.mark.asyncio
async def test_discover_returns_empty_list_on_request_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    session = SessionManager.get_instance(transport=httpx.MockTransport(handler), retry_policy=_FAST_RETRY_POLICY)
    await session.startup()

    provider = DuckDuckGoSearchProvider(session_manager=session)
    results = await provider.discover("query", "", limit=10)

    assert results == []


def test_unwrap_redirect_passes_through_direct_links() -> None:
    direct = "https://www.instagram.com/starbucks/"
    assert DuckDuckGoSearchProvider._unwrap_redirect(direct) == direct
