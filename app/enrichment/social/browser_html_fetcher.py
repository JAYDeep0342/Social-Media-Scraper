"""Fetches a business's homepage HTML via a pooled Playwright page instead
of a plain HTTP GET.

Verified live: several real business sites return a near-empty response to
a plain httpx GET (e.g. spanarchitects.in: 14 bytes; rkgaltd.com: 272
bytes) -- a bare redirect stub, not the real page -- yet a real browser
render of the same URL pulls in 130-200KB of actual content, including
footer Instagram/Facebook links that were never present in the raw HTTP
response at all. Reuses the same browser pool Maps discovery/enrichment
already use, rather than opening a second browser.

Also verified live: fetching ~10 sites through this fetcher concurrently
(one shared browser, one page each, all navigating at once -- exactly what
the social-discovery worker pool does) made roughly half of them exceed a
15s navigation timeout, even though every one of them loads fine in a few
seconds run alone -- one Chromium process rendering 10 full pages
(images, fonts, third-party scripts) at once saturates CPU/network. We
only need the DOM's anchor hrefs, not a visual render, so images/fonts/
media/stylesheets are blocked at the network level below: it cuts page
weight dramatically and lets real concurrency happen without the pile-up.
"""

from typing import Any, Optional

from playwright.async_api import Route

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet"}


async def _block_heavy_resources(route: Route) -> None:
    if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
        await route.abort()
    else:
        await route.continue_()


class BrowserWebsiteHTMLFetcher:
    def __init__(self, browser_pool: Any) -> None:
        self._browser_pool = browser_pool

    async def fetch(self, url: str) -> Optional[str]:
        settings = get_settings()
        try:
            async with self._browser_pool.acquire() as page:
                await page.route("**/*", _block_heavy_resources)
                try:
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=settings.SOCIAL_BROWSER_FETCH_TIMEOUT_SECONDS * 1000,
                    )
                    try:
                        await page.wait_for_load_state(
                            "networkidle", timeout=settings.SOCIAL_BROWSER_NETWORKIDLE_TIMEOUT_SECONDS * 1000
                        )
                    except Exception:
                        pass  # slow/streaming page -- use whatever has rendered so far
                    return await page.content()
                finally:
                    await page.unroute("**/*", _block_heavy_resources)
        except Exception:
            logger.warning("Browser fetch failed for %s", url, exc_info=True)
            return None
