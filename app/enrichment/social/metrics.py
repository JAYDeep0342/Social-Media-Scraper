"""Outcome metrics for a social discovery batch: HTML fetch success rate,
website-extraction success, how often the search fallback was needed,
Instagram/Facebook find counts, and average per-business processing time.
Async-lock-protected, mirroring app.network.network_metrics (Phase 2) and
app.enrichment.google_maps.metrics (Phase 4).
"""

import asyncio
import time
from dataclasses import dataclass


@dataclass
class SocialDiscoveryMetricsSnapshot:
    total_processed: int
    html_fetch_success: int
    website_success: int
    search_fallback_used: int
    instagram_found: int
    facebook_found: int
    average_processing_seconds: float


class SocialDiscoveryMetrics:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._total_processed = 0
        self._html_fetch_success = 0
        self._website_success = 0
        self._search_fallback_used = 0
        self._instagram_found = 0
        self._facebook_found = 0
        self._total_time = 0.0

    async def start_one(self) -> float:
        return time.perf_counter()

    async def record_html_fetch(self, success: bool) -> None:
        if not success:
            return
        async with self._lock:
            self._html_fetch_success += 1

    async def record_website_success(self) -> None:
        async with self._lock:
            self._website_success += 1

    async def record_search_fallback_used(self) -> None:
        async with self._lock:
            self._search_fallback_used += 1

    async def finish_one(self, start_time: float, *, instagram_found: bool, facebook_found: bool) -> None:
        elapsed = time.perf_counter() - start_time
        async with self._lock:
            self._total_processed += 1
            self._total_time += elapsed
            if instagram_found:
                self._instagram_found += 1
            if facebook_found:
                self._facebook_found += 1

    async def snapshot(self) -> SocialDiscoveryMetricsSnapshot:
        async with self._lock:
            average_time = (self._total_time / self._total_processed) if self._total_processed else 0.0
            return SocialDiscoveryMetricsSnapshot(
                total_processed=self._total_processed,
                html_fetch_success=self._html_fetch_success,
                website_success=self._website_success,
                search_fallback_used=self._search_fallback_used,
                instagram_found=self._instagram_found,
                facebook_found=self._facebook_found,
                average_processing_seconds=round(average_time, 3),
            )

    async def reset(self) -> None:
        async with self._lock:
            self._total_processed = 0
            self._html_fetch_success = 0
            self._website_success = 0
            self._search_fallback_used = 0
            self._instagram_found = 0
            self._facebook_found = 0
            self._total_time = 0.0
