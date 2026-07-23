"""Opens a business's Google Maps detail panel directly via its Maps URL.

Must be given the FULL, unmodified Maps URL as captured by the discovery
engine (Phase 3) — verified live: navigating to a truncated/reconstructed
URL (missing the trailing place-id segment and query params) causes Google
to fall back to a generic map view instead of opening the intended place.

Transient Playwright failures are retried using Phase 2's retry engine
(app.network.retry_strategy.RetryPolicy) rather than a new retry mechanism.
"""

from typing import Optional

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.config.settings import get_settings
from app.enrichment.google_maps import selectors
from app.exceptions.errors import ExtractionError, ScraperTimeoutError
from app.network.retry_strategy import RetryPolicy


def default_detail_retry_policy() -> RetryPolicy:
    settings = get_settings()
    return RetryPolicy(
        max_attempts=settings.MAX_RETRIES + 1,
        base_delay=settings.RETRY_BACKOFF_BASE,
        max_delay=settings.RETRY_MAX_DELAY_SECONDS,
        jitter=settings.RETRY_JITTER_SECONDS,
        retryable_exceptions=(ScraperTimeoutError, ExtractionError),
    )


class DetailPanelNavigator:
    def __init__(
        self,
        page: Page,
        *,
        navigation_timeout_seconds: Optional[float] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        settings = get_settings()
        self._page = page
        self._timeout_ms = (navigation_timeout_seconds or settings.BROWSER_NAVIGATION_TIMEOUT_SECONDS) * 1000
        self._retry_policy = retry_policy or default_detail_retry_policy()

    async def open(self, maps_url: str) -> None:
        async def _navigate() -> None:
            try:
                await self._page.goto(maps_url, timeout=self._timeout_ms)
                await self._page.wait_for_selector(selectors.DETAIL_PANEL_ROOT, timeout=self._timeout_ms)
            except PlaywrightTimeoutError as exc:
                raise ScraperTimeoutError(f"Timed out opening detail panel for {maps_url}") from exc
            except Exception as exc:
                raise ExtractionError(f"Failed to open detail panel for {maps_url}") from exc

        await self._retry_policy.execute(_navigate, label=f"open detail panel ({maps_url})")
