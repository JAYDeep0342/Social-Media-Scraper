from unittest.mock import AsyncMock, MagicMock

import pytest

from app.discovery.google_maps.browser_manager import BrowserManager


def _fake_async_playwright(monkeypatch, *, launch_side_effect=None):
    fake_browser = MagicMock()
    fake_browser.is_connected.return_value = True
    fake_browser.close = AsyncMock()

    fake_chromium = MagicMock()
    if launch_side_effect is not None:
        fake_chromium.launch = AsyncMock(side_effect=launch_side_effect)
    else:
        fake_chromium.launch = AsyncMock(return_value=fake_browser)

    fake_playwright_instance = MagicMock()
    fake_playwright_instance.chromium = fake_chromium
    fake_playwright_instance.stop = AsyncMock()

    fake_playwright_ctx = MagicMock()
    fake_playwright_ctx.start = AsyncMock(return_value=fake_playwright_instance)

    monkeypatch.setattr(
        "app.discovery.google_maps.browser_manager.async_playwright",
        lambda: fake_playwright_ctx,
    )
    return fake_browser, fake_playwright_instance


@pytest.mark.asyncio
async def test_start_launches_chromium_and_returns_browser(monkeypatch) -> None:
    fake_browser, _ = _fake_async_playwright(monkeypatch)
    manager = BrowserManager(headless=True)

    browser = await manager.start()

    assert browser is fake_browser
    assert manager.is_running is True


@pytest.mark.asyncio
async def test_start_is_idempotent_reuses_existing_browser(monkeypatch) -> None:
    fake_browser, fake_playwright_instance = _fake_async_playwright(monkeypatch)
    manager = BrowserManager(headless=True)

    first = await manager.start()
    second = await manager.start()

    assert first is second
    fake_playwright_instance.chromium.launch.assert_called_once()


@pytest.mark.asyncio
async def test_browser_property_raises_before_start() -> None:
    manager = BrowserManager(headless=True)
    with pytest.raises(RuntimeError):
        _ = manager.browser


@pytest.mark.asyncio
async def test_launch_failure_raises_discovery_error(monkeypatch) -> None:
    from app.exceptions.errors import DiscoveryError

    _fake_async_playwright(monkeypatch, launch_side_effect=RuntimeError("no chromium binary"))
    manager = BrowserManager(headless=True)

    with pytest.raises(DiscoveryError):
        await manager.start()


@pytest.mark.asyncio
async def test_stop_closes_browser_and_playwright(monkeypatch) -> None:
    fake_browser, fake_playwright_instance = _fake_async_playwright(monkeypatch)
    manager = BrowserManager(headless=True)
    await manager.start()

    await manager.stop()

    fake_browser.close.assert_called_once()
    fake_playwright_instance.stop.assert_called_once()
    assert manager.is_running is False
