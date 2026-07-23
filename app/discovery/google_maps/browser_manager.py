"""Owns the Playwright process and a single reusable Browser instance.

Responsible for launching Playwright, browser lifecycle, and graceful
shutdown. Does not manage contexts/pages — see browser_pool.py for that.
"""

from typing import Optional

from playwright.async_api import Browser, Playwright, async_playwright

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.exceptions.errors import DiscoveryError

logger = get_logger(__name__)


class BrowserManager:
    def __init__(self, *, headless: Optional[bool] = None) -> None:
        settings = get_settings()
        self._headless = settings.BROWSER_HEADLESS if headless is None else headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def start(self) -> Browser:
        """Idempotent: returns the existing browser if already running,
        otherwise launches Chromium and reuses that single instance."""
        if self._browser is not None and self._browser.is_connected():
            return self._browser

        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.launch(headless=self._headless)
        except Exception as exc:
            await self._playwright.stop()
            self._playwright = None
            raise DiscoveryError("Failed to launch Chromium via Playwright") from exc

        logger.info("Playwright Chromium browser launched (headless=%s)", self._headless)
        return self._browser

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            raise RuntimeError("BrowserManager.start() must be called before use")
        return self._browser

    @property
    def is_running(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Playwright browser stopped")
