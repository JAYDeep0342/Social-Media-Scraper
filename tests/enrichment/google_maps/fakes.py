"""A minimal, purpose-built fake of the Playwright async API surface the
website enrichment code uses — mirrors
tests/discovery/google_maps/fakes.py's approach (dispatch on exact
selector strings rather than a general CSS engine).
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Optional

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.enrichment.google_maps import selectors


class FakeElementLocator:
    def __init__(self, *, href: Optional[str] = None, count_override: Optional[int] = None) -> None:
        self._href = href
        self._count = 1 if count_override is None else count_override

    async def count(self) -> int:
        return self._count

    @property
    def first(self) -> "FakeElementLocator":
        return self

    async def get_attribute(self, name: str) -> Optional[str]:
        return self._href if name == "href" else None


class FakeDetailPage:
    """Simulates a Google Maps detail panel. Supports two modes:

    - Single-business mode (`website`/`fail_open`/`transient_failures`):
      this page always represents one business — enough for testing the
      navigator/extractor in isolation.
    - Multi-business mode (`url_to_website`/`fail_urls`): the page looks up
      its current business by whatever URL was last `goto()`'d, mirroring
      how a real pooled Playwright page is reused across many businesses.
      Needed for batch/worker tests where several distinct businesses
      share a small pool of pages.
    """

    def __init__(
        self,
        *,
        website: Optional[str] = None,
        fail_open: bool = False,
        transient_failures: int = 0,
        url_to_website: Optional[dict] = None,
        fail_urls: Optional[set] = None,
    ) -> None:
        self.website = website
        self.fail_open = fail_open
        self.transient_failures = transient_failures
        self.url_to_website = url_to_website
        self.fail_urls = fail_urls or set()
        self.calls: List[tuple] = []
        self._wait_attempts = 0
        self.current_url: Optional[str] = None

    async def goto(self, url: str, timeout: Optional[float] = None) -> None:
        self.current_url = url
        self.calls.append(("goto", url))

    async def wait_for_selector(self, selector: str, timeout: Optional[float] = None) -> None:
        self._wait_attempts += 1
        if self.fail_open or self.current_url in self.fail_urls:
            raise PlaywrightTimeoutError(f"Timeout waiting for {selector}")
        if self._wait_attempts <= self.transient_failures:
            raise PlaywrightTimeoutError(f"Transient timeout waiting for {selector} (attempt {self._wait_attempts})")
        self.calls.append(("wait_for_selector", selector))

    def locator(self, selector: str):
        if selector == selectors.WEBSITE_LINK:
            website = self.url_to_website.get(self.current_url) if self.url_to_website is not None else self.website
            if website:
                return FakeElementLocator(href=website)
            return FakeElementLocator(count_override=0)
        raise ValueError(f"Unhandled selector in fake: {selector}")


class FakePool:
    """Minimal fake of BrowserContextPool: hands out one of `pages` at a
    time via an asyncio.Queue, exactly like the real pool's acquire/release
    semantics, so concurrent workers never share a single page at once."""

    def __init__(self, pages: List[FakeDetailPage]) -> None:
        import asyncio

        self._queue: "asyncio.Queue[FakeDetailPage]" = asyncio.Queue()
        for page in pages:
            self._queue.put_nowait(page)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[FakeDetailPage]:
        page = await self._queue.get()
        try:
            yield page
        finally:
            await self._queue.put(page)
