import pytest

from app.exceptions.errors import ScraperTimeoutError
from app.discovery.google_maps.maps_navigator import MapsNavigator
from tests.discovery.google_maps.fakes import FakePage


@pytest.mark.asyncio
async def test_search_navigates_fills_and_waits_for_feed() -> None:
    page = FakePage(cards=[])
    navigator = MapsNavigator(page)

    await navigator.search("coffee shops", "Seattle, WA")

    call_kinds = [call[0] for call in page.calls]
    assert call_kinds == ["goto", "wait_for_selector", "fill", "press", "wait_for_selector"]
    assert page.calls[2] == ("fill", "input[name=\"q\"]", "coffee shops in Seattle, WA")
    assert page.calls[3] == ("press", "input[name=\"q\"]", "Enter")


@pytest.mark.asyncio
async def test_search_raises_scraper_timeout_on_playwright_timeout() -> None:
    page = FakePage(cards=[], fail_search=True)
    navigator = MapsNavigator(page)

    with pytest.raises(ScraperTimeoutError):
        await navigator.search("coffee shops", "Seattle, WA")
