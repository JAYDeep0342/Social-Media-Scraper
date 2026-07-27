"""Fakes for exercising the full orchestrator end-to-end without a real
browser or network. `FakeOrchestratorPage` understands BOTH the discovery
stage's selectors (search results feed) and the enrichment stage's
selectors (detail panel), so one small fake pool can be shared across
both stages exactly like the real BrowserContextPool is in production.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, List, Optional

from app.discovery.google_maps import selectors as d_selectors
from app.enrichment.google_maps import selectors as e_selectors


class FakeCard:
    def __init__(self, name: str, maps_url: str) -> None:
        self.name = name
        self.maps_url = maps_url


class FakeElementLocator:
    def __init__(
        self, *, href: Optional[str] = None, aria_label: Optional[str] = None, count_override: Optional[int] = None
    ) -> None:
        self._href = href
        self._aria_label = aria_label
        self._count = 1 if count_override is None else count_override

    async def count(self) -> int:
        return self._count

    @property
    def first(self) -> "FakeElementLocator":
        return self

    async def get_attribute(self, name: str) -> Optional[str]:
        if name == "href":
            return self._href
        if name == "aria-label":
            return self._aria_label
        return None

    async def text_content(self) -> Optional[str]:
        return None


class FakeCountLocator:
    def __init__(self, count_fn) -> None:
        self._count_fn = count_fn

    async def count(self) -> int:
        return self._count_fn()


class FakeContainerLocator:
    def __init__(self, card: FakeCard) -> None:
        self._card = card

    def locator(self, sub_selector: str):
        if sub_selector == d_selectors.RESULT_CARD_LINK_RELATIVE:
            return FakeElementLocator(href=self._card.maps_url, aria_label=self._card.name)
        if sub_selector in (d_selectors.RESULT_CARD_NAME, d_selectors.RESULT_CARD_WEBSITE_LINK):
            return FakeElementLocator(count_override=0)
        raise ValueError(f"Unhandled sub-selector in fake: {sub_selector}")


class FakeContainerListLocator:
    def __init__(self, page: "FakeOrchestratorPage") -> None:
        self._page = page

    async def count(self) -> int:
        return len(self._page.cards)

    def nth(self, index: int) -> FakeContainerLocator:
        return FakeContainerLocator(self._page.cards[index])


class FakeFeedLocator:
    async def count(self) -> int:
        return 1

    async def evaluate(self, js: str) -> None:
        return None  # all cards are revealed from the start in this fixture


class FakeOrchestratorPage:
    """Behaves as the Google Maps search results page while `cards` is
    being scanned (Discovery), and as a place's detail panel once
    navigated to a specific place URL (Enrichment) — `url_to_website`
    maps each such URL to what WEBSITE_LINK should resolve to.
    """

    def __init__(self, *, cards: List[FakeCard], url_to_website: Dict[str, Optional[str]]) -> None:
        self.cards = cards
        self.url_to_website = url_to_website
        self.current_url: Optional[str] = None
        self.calls: List[tuple] = []

    async def goto(self, url: str, timeout: Optional[float] = None) -> None:
        self.current_url = url
        self.calls.append(("goto", url))

    async def wait_for_selector(self, selector: str, timeout: Optional[float] = None) -> None:
        self.calls.append(("wait_for_selector", selector))

    async def fill(self, selector: str, value: str) -> None:
        self.calls.append(("fill", selector, value))

    async def press(self, selector: str, key: str) -> None:
        self.calls.append(("press", selector, key))

    def locator(self, selector: str):
        if selector == d_selectors.RESULTS_FEED:
            return FakeFeedLocator()
        if selector == d_selectors.RESULT_CARD_LINK:
            return FakeCountLocator(lambda: len(self.cards))
        if selector == d_selectors.RESULT_CARD_CONTAINER:
            return FakeContainerListLocator(self)
        if selector.startswith("text="):
            return FakeCountLocator(lambda: 0)
        if selector == e_selectors.WEBSITE_LINK:
            website = self.url_to_website.get(self.current_url)
            return FakeElementLocator(href=website) if website else FakeElementLocator(count_override=0)
        raise ValueError(f"Unhandled selector in fake: {selector}")

    async def evaluate(self, script: str, arg=None) -> list:
        """Simulates CardExtractor's single batched page.evaluate() call
        for discovery: one dict per card, website always None (matching
        this fake's existing discovery-never-exposes-a-website behavior;
        enrichment fills it in separately via WEBSITE_LINK above)."""
        return [{"mapsUrl": card.maps_url, "rawName": card.name, "website": None} for card in self.cards]


class FakeOrchestratorPool:
    """Minimal fake of BrowserContextPool: hands out one of `pages` at a
    time via an asyncio.Queue, exactly like the real pool's acquire/
    release semantics, so concurrent stages never share a page at once."""

    def __init__(self, pages: List[FakeOrchestratorPage]) -> None:
        self._queue: "asyncio.Queue[FakeOrchestratorPage]" = asyncio.Queue()
        for page in pages:
            self._queue.put_nowait(page)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[FakeOrchestratorPage]:
        page = await self._queue.get()
        try:
            yield page
        finally:
            await self._queue.put(page)


class FakeSocialExtractor:
    """Cooperates with FakeSocialFetcher via `current_website` (set by the
    fetcher right before extract() is called), mirroring the fetcher/
    extractor cooperation pattern used in Phase 5's own tests."""

    def __init__(self, candidates_by_website: Dict[str, list]) -> None:
        self.candidates_by_website = candidates_by_website
        self.current_website: Optional[str] = None

    def extract(self, html: str) -> list:
        return self.candidates_by_website.get(self.current_website, [])


class FakeSocialFetcher:
    def __init__(self, extractor: FakeSocialExtractor) -> None:
        self._extractor = extractor

    async def fetch(self, url: str) -> str:
        self._extractor.current_website = url
        return "<html></html>"


class FakeSocialFallback:
    async def find(self, business_name: str, platform: str):
        return None, False
