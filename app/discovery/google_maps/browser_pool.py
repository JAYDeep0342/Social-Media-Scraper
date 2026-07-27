"""Pool of reusable Playwright BrowserContext + Page pairs, so discovery
and enrichment tasks borrow an already-warm page instead of paying
context/page creation cost on every search/navigation. Configurable pool
size; entries are created concurrently at startup so a larger pool
doesn't cost proportionally more wall-clock time to warm up.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Optional

from playwright.async_api import BrowserContext, Page

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.discovery.google_maps.browser_manager import BrowserManager

logger = get_logger(__name__)


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
        results = await asyncio.gather(
            *(self._create_entry(browser) for _ in range(self._pool_size)),
            return_exceptions=True,
        )

        first_error: Optional[BaseException] = None
        for result in results:
            if isinstance(result, BaseException):
                if first_error is None:
                    first_error = result
                continue
            self._all.append(result)
            await self._pool.put(result)

        if first_error is not None:
            # Whatever entries DID succeed are already tracked in
            # self._all/self._pool above, so the caller's stop() (always
            # called from the orchestrator's finally block) will still
            # close them -- nothing created here is leaked even though
            # start() itself is failing.
            raise first_error
        self._started = True

    async def _create_entry(self, browser) -> _PooledPage:
        settings = get_settings()
        context = await browser.new_context(
            viewport={"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT}
        )
        try:
            page = await context.new_page()
        except Exception:
            await context.close()
            raise
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
            try:
                await entry.context.close()
            except Exception:
                logger.exception("Error closing a pooled browser context; continuing to close the rest")
        self._all.clear()
        self._pool = asyncio.Queue()
        self._started = False

    @property
    def size(self) -> int:
        return len(self._all)

    @property
    def is_started(self) -> bool:
        return self._started
