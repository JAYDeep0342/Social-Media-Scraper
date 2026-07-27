"""A minimal, purpose-built fake of the Playwright async API surface our
Google Maps discovery code uses. Not a general CSS engine — it dispatches
on the exact selector strings defined in app.discovery.google_maps.selectors,
which keeps the fake simple while still exercising the real code paths.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.discovery.google_maps import selectors


@dataclass
class FakeCard:
    name: Optional[str] = "Test Business"
    maps_url: Optional[str] = (
        "https://www.google.com/maps/place/Test+Business/data=!4m7!3m6!1s0x1:0x1!8m2!3d0!4d0"
    )
    website: Optional[str] = None
    name_only_via_class: bool = False  # aria-label absent; name comes from .qBF1Pd instead
    no_link: bool = False  # the card has no link element at all


class FakeElementLocator:
    def __init__(
        self,
        *,
        href: Optional[str] = None,
        text: Optional[str] = None,
        aria_label: Optional[str] = None,
        count_override: Optional[int] = None,
    ) -> None:
        self._href = href
        self._text = text
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
        return self._text


class FakeCountLocator:
    def __init__(self, count_fn: Callable[[], int]) -> None:
        self._count_fn = count_fn

    async def count(self) -> int:
        return self._count_fn()


class FakeContainerLocator:
    def __init__(self, card: FakeCard) -> None:
        self._card = card

    def locator(self, sub_selector: str):
        if sub_selector == selectors.RESULT_CARD_LINK_RELATIVE:
            if self._card.no_link:
                return FakeElementLocator(count_override=0)
            return FakeElementLocator(
                href=self._card.maps_url,
                aria_label=None if self._card.name_only_via_class else self._card.name,
            )
        if sub_selector == selectors.RESULT_CARD_NAME:
            if self._card.name_only_via_class and self._card.name:
                return FakeElementLocator(text=self._card.name)
            return FakeElementLocator(count_override=0)
        if sub_selector == selectors.RESULT_CARD_WEBSITE_LINK:
            if self._card.website:
                return FakeElementLocator(href=self._card.website)
            return FakeElementLocator(count_override=0)
        raise ValueError(f"Unhandled sub-selector in fake: {sub_selector}")


class FakeContainerListLocator:
    def __init__(self, page: "FakePage") -> None:
        self._page = page

    async def count(self) -> int:
        return self._page.revealed

    def nth(self, index: int) -> FakeContainerLocator:
        return FakeContainerLocator(self._page.cards[index])


class FakeFeedLocator:
    def __init__(self, page: "FakePage") -> None:
        self._page = page

    async def count(self) -> int:
        return 1

    async def evaluate(self, js: str) -> None:
        self._page.reveal_more()


class FakePage:
    """Simulates a Google Maps results page: `cards` is the full dataset,
    `reveal_schedule` controls how many are "loaded" after each scroll
    (mirrors the real stair-step pattern observed against live Maps, e.g.
    [6, 12, 12, 20, 20, 20]); once the schedule is exhausted the count
    plateaus, simulating end-of-list.
    """

    def __init__(
        self,
        cards: List[FakeCard],
        *,
        reveal_schedule: Optional[List[int]] = None,
        fail_search: bool = False,
        simulate_end_marker_after: Optional[int] = None,
    ) -> None:
        self.cards = cards
        self.reveal_schedule = reveal_schedule
        self.fail_search = fail_search
        self.simulate_end_marker_after = simulate_end_marker_after
        self._scroll_calls = 0
        self.revealed = reveal_schedule[0] if reveal_schedule else len(cards)
        self.calls: List[tuple] = []

    async def goto(self, url: str, timeout: Optional[float] = None) -> None:
        self.calls.append(("goto", url))

    async def wait_for_selector(self, selector: str, timeout: Optional[float] = None) -> None:
        if self.fail_search:
            raise PlaywrightTimeoutError(f"Timeout waiting for {selector}")
        self.calls.append(("wait_for_selector", selector))

    async def fill(self, selector: str, value: str) -> None:
        self.calls.append(("fill", selector, value))

    async def press(self, selector: str, key: str) -> None:
        self.calls.append(("press", selector, key))

    def locator(self, selector: str):
        if selector == selectors.RESULTS_FEED:
            return FakeFeedLocator(self)
        if selector == selectors.RESULT_CARD_LINK:
            return FakeCountLocator(lambda: self.revealed)
        if selector == selectors.RESULT_CARD_CONTAINER:
            return FakeContainerListLocator(self)
        if selector.startswith("text="):
            return FakeCountLocator(lambda: 1 if self._end_marker_reached() else 0)
        raise ValueError(f"Unhandled selector in fake: {selector}")

    async def evaluate(self, script: str, arg=None) -> list:
        """Simulates CardExtractor's single batched page.evaluate() call:
        one dict per currently-revealed card (mirroring what the real
        in-page JS would produce), or None for a card missing a link/name
        — same skip semantics as the real script."""
        results = []
        for card in self.cards[: self.revealed]:
            if card.no_link or not card.name:
                results.append(None)
                continue
            results.append({"mapsUrl": card.maps_url, "rawName": card.name, "website": card.website})
        return results

    def _end_marker_reached(self) -> bool:
        return (
            self.simulate_end_marker_after is not None
            and self._scroll_calls >= self.simulate_end_marker_after
        )

    def reveal_more(self) -> None:
        self._scroll_calls += 1
        if self.reveal_schedule:
            idx = min(self._scroll_calls, len(self.reveal_schedule) - 1)
            self.revealed = self.reveal_schedule[idx]
        else:
            self.revealed = len(self.cards)
