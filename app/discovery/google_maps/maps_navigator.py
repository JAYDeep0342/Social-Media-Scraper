"""Navigates a Playwright Page to Google Maps and performs a keyword+location
search, waiting for the results feed to be ready before returning control.
"""

from typing import Optional

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.config.constants import GOOGLE_MAPS_BASE_URL
from app.config.settings import get_settings
from app.discovery.google_maps import selectors
from app.exceptions.errors import DiscoveryError, ScraperTimeoutError


class MapsNavigator:
    def __init__(self, page: Page, *, navigation_timeout_seconds: Optional[float] = None) -> None:
        settings = get_settings()
        self._page = page
        self._timeout_ms = (navigation_timeout_seconds or settings.BROWSER_NAVIGATION_TIMEOUT_SECONDS) * 1000

    async def search(self, keyword: str, location: str) -> None:
        query = f"{keyword} in {location}"
        try:
            await self._page.goto(GOOGLE_MAPS_BASE_URL, timeout=self._timeout_ms)
            await self._page.wait_for_selector(selectors.SEARCH_BOX_INPUT, timeout=self._timeout_ms)
            await self._page.fill(selectors.SEARCH_BOX_INPUT, query)
            await self._page.press(selectors.SEARCH_BOX_INPUT, "Enter")
            await self._page.wait_for_selector(selectors.RESULTS_FEED, timeout=self._timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ScraperTimeoutError(f"Timed out loading Google Maps results for '{query}'") from exc
        except Exception as exc:
            raise DiscoveryError(f"Failed to search Google Maps for '{query}'") from exc
