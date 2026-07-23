import httpx
import pytest

from app.network.http_client import HTTPClientManager


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_request_returns_response_via_mock_transport() -> None:
    manager = HTTPClientManager(transport=_mock_transport())
    response = await manager.request("GET", "https://example.test/ping")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    await manager.aclose()


@pytest.mark.asyncio
async def test_aclose_is_idempotent_and_marks_closed() -> None:
    manager = HTTPClientManager(transport=_mock_transport())
    await manager.aclose()
    assert manager.is_closed
    await manager.aclose()  # must not raise on a second close


@pytest.mark.asyncio
async def test_falls_back_to_http1_when_h2_unavailable(monkeypatch) -> None:
    def _raise_import_error(*args, **kwargs):
        raise ImportError("h2 package is not installed")

    real_async_client = httpx.AsyncClient
    call_count = {"n": 0}

    def fake_async_client(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            _raise_import_error()
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)
    manager = HTTPClientManager(transport=_mock_transport())
    assert call_count["n"] == 2
    await manager.aclose()
