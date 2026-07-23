"""Pool of reusable Playwright BrowserContext + Page pairs, so discovery
tasks borrow an already-warm page instead of paying context/page creation
cost on every search. Configurable pool size.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Optional

from playwright.async_api import BrowserContext, Page

from app.config.settings import get_settings
from app.discovery.google_maps.browser_manager import BrowserManager


class _PooledPage:
    __slots__ = ("context", "page")

    def __init__(self, context: BrowserContext, page: Page) -> None:
        self.context = context
        self.page = page


class BrowserContextPool:
    def __init__(self, browser_manager: BrowserManager, *, pool_size: Optional[int] = None) -> None:
        settings = get_settings()
        self._browser_manager = browser_manager
        self._pool_size = pool_size or settings.BROWSER_POOL_SIZE
        self._pool: "asyncio.Queue[_PooledPage]" = asyncio.Queue()
        self._all: List[_PooledPage] = []
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        browser = self._browser_manager.browser
        for _ in range(self._pool_size):
            entry = await self._create_entry(browser)
            self._all.append(entry)
            await self._pool.put(entry)
        self._started = True

    async def _create_entry(self, browser) -> _PooledPage:
        settings = get_settings()
        context = await browser.new_context(
            viewport={"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT}
        )
        page = await context.new_page()
        return _PooledPage(context=context, page=page)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Page]:
        entry = await self._pool.get()
        try:
            yield entry.page
        finally:
            await self._pool.put(entry)

    async def stop(self) -> None:
        for entry in self._all:
            await entry.context.close()
        self._all.clear()
        self._pool = asyncio.Queue()
        self._started = False

    @property
    def size(self) -> int:
        return len(self._all)

    @property
    def is_started(self) -> bool:
        return self._started
