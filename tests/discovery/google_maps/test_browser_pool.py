import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.discovery.google_maps.browser_pool import BrowserContextPool


def _fake_manager_with_browser():
    page = MagicMock()
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    context.close = AsyncMock()

    browser = MagicMock()
    browser.new_context = AsyncMock(return_value=context)

    manager = MagicMock()
    manager.browser = browser
    return manager, browser, context, page


@pytest.mark.asyncio
async def test_start_creates_pool_size_entries() -> None:
    manager, browser, context, _page = _fake_manager_with_browser()
    pool = BrowserContextPool(manager, pool_size=3)

    await pool.start()

    assert pool.size == 3
    assert browser.new_context.call_count == 3
    assert context.new_page.call_count == 3


@pytest.mark.asyncio
async def test_start_is_idempotent() -> None:
    manager, browser, _context, _page = _fake_manager_with_browser()
    pool = BrowserContextPool(manager, pool_size=2)

    await pool.start()
    await pool.start()

    assert browser.new_context.call_count == 2


@pytest.mark.asyncio
async def test_acquire_yields_a_page_and_returns_it_to_the_pool() -> None:
    manager, _browser, _context, page = _fake_manager_with_browser()
    pool = BrowserContextPool(manager, pool_size=1)
    await pool.start()

    async with pool.acquire() as acquired_page:
        assert acquired_page is page

    async with pool.acquire() as acquired_again:
        assert acquired_again is page


@pytest.mark.asyncio
async def test_acquire_blocks_until_release_when_pool_exhausted() -> None:
    manager, _browser, _context, _page = _fake_manager_with_browser()
    pool = BrowserContextPool(manager, pool_size=1)
    await pool.start()

    acquired_event = asyncio.Event()
    released = False

    async def hold_and_release() -> None:
        nonlocal released
        async with pool.acquire():
            acquired_event.set()
            await asyncio.sleep(0.05)
            released = True

    task = asyncio.create_task(hold_and_release())
    await acquired_event.wait()

    async with pool.acquire():
        assert released is True

    await task


@pytest.mark.asyncio
async def test_stop_closes_all_contexts() -> None:
    manager, _browser, context, _page = _fake_manager_with_browser()
    pool = BrowserContextPool(manager, pool_size=2)
    await pool.start()

    await pool.stop()

    assert context.close.call_count == 2
    assert pool.size == 0
