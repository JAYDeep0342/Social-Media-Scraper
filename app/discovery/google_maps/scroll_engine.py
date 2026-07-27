"""Scrolls the Google Maps results feed, adaptively backing off when no new
cards appear, and stops on reaching the requested limit or the end of the
list.

Verified against live Google Maps: the result count grows in a stair-step
pattern across scrolls (e.g. 6 -> 12 -> 12 -> 20 -> 20 -> 20 -> 20), so a
single unproductive scroll is not itself a reliable end-of-list signal —
the load-bearing signal is the count staying flat for several consecutive
attempts (`max_attempts_without_progress`). A textual end-of-list marker is
checked too, but wasn't observed in verification and should be treated as a
low-confidence secondary signal only.

Each scroll's pause window is a poll loop, not a flat sleep: it re-checks
the card count every `SCROLL_POLL_INTERVAL_SECONDS` and returns as soon as
new cards appear, instead of always sleeping the full (possibly backed-off)
pause. A scroll that's genuinely stalled still waits out the full window —
only a scroll that loads faster than the window gets to finish early.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import Page

from app.config.settings import get_settings
from app.discovery.google_maps import selectors


@dataclass
class ScrollResult:
    scroll_count: int
    reached_end_of_list: bool
    reached_limit: bool


class ScrollEngine:
    def __init__(
        self,
        page: Page,
        *,
        base_pause_seconds: Optional[float] = None,
        max_attempts_without_progress: Optional[int] = None,
        max_total_attempts: Optional[int] = None,
        poll_interval_seconds: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self._page = page
        self._base_pause = base_pause_seconds or settings.SCROLL_PAUSE_SECONDS
        self._max_stall = max_attempts_without_progress or settings.SCROLL_MAX_ATTEMPTS_WITHOUT_PROGRESS
        self._max_total = max_total_attempts or settings.SCROLL_MAX_TOTAL_ATTEMPTS
        self._poll_interval = poll_interval_seconds or settings.SCROLL_POLL_INTERVAL_SECONDS

    async def _card_count(self) -> int:
        return await self._page.locator(selectors.RESULT_CARD_LINK).count()

    async def _is_end_of_list(self) -> bool:
        return await self._page.locator(f"text={selectors.END_OF_LIST_TEXT}").count() > 0

    async def _wait_for_progress_or_timeout(self, previous_count: int, timeout: float) -> int:
        """Polls the card count instead of sleeping the full `timeout`
        unconditionally, returning the new count as soon as it exceeds
        `previous_count`. Always waits at least one poll interval, so a
        stalled scroll still gets the full window before being judged."""
        elapsed = 0.0
        current_count = previous_count
        while elapsed < timeout:
            interval = min(self._poll_interval, timeout - elapsed)
            await asyncio.sleep(interval)
            elapsed += interval
            current_count = await self._card_count()
            if current_count > previous_count:
                return current_count
        return current_count

    async def scroll_until(self, limit: int) -> ScrollResult:
        stall_count = 0
        total_attempts = 0
        pause = self._base_pause
        previous_count = await self._card_count()

        while total_attempts < self._max_total:
            if previous_count >= limit:
                return ScrollResult(total_attempts, reached_end_of_list=False, reached_limit=True)
            if await self._is_end_of_list():
                return ScrollResult(total_attempts, reached_end_of_list=True, reached_limit=False)

            await self._page.locator(selectors.RESULTS_FEED).evaluate("el => el.scrollBy(0, el.scrollHeight)")
            total_attempts += 1
            current_count = await self._wait_for_progress_or_timeout(previous_count, pause)

            if current_count <= previous_count:
                stall_count += 1
                pause = min(pause * 1.5, self._base_pause * 4)  # adaptive backoff while stalled
                if stall_count >= self._max_stall:
                    return ScrollResult(total_attempts, reached_end_of_list=True, reached_limit=False)
            else:
                stall_count = 0
                pause = self._base_pause  # reset once progress resumes
            previous_count = current_count

        return ScrollResult(total_attempts, reached_end_of_list=False, reached_limit=False)
