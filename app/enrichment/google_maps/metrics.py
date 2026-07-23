"""Outcome metrics for a batch enrichment run: total enriched, how many
still have no website afterward, success rate, and average enrichment time
per processed lead. Async-lock-protected, mirroring
app.network.network_metrics's pattern (Phase 2).
"""

import asyncio
import time
from dataclasses import dataclass


@dataclass
class EnrichmentMetricsSnapshot:
    total_enriched: int
    missing_websites: int
    success_rate: float
    average_enrichment_seconds: float


class EnrichmentMetrics:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._total = 0
        self._missing = 0
        self._total_time = 0.0

    async def start_one(self) -> float:
        return time.perf_counter()

    async def finish_one(self, start_time: float, *, success: bool) -> None:
        elapsed = time.perf_counter() - start_time
        async with self._lock:
            self._total += 1
            self._total_time += elapsed
            if not success:
                self._missing += 1

    async def snapshot(self) -> EnrichmentMetricsSnapshot:
        async with self._lock:
            success_count = self._total - self._missing
            success_rate = (success_count / self._total * 100) if self._total else 0.0
            average_time = (self._total_time / self._total) if self._total else 0.0
            return EnrichmentMetricsSnapshot(
                total_enriched=self._total,
                missing_websites=self._missing,
                success_rate=round(success_rate, 2),
                average_enrichment_seconds=round(average_time, 3),
            )

    async def reset(self) -> None:
        async with self._lock:
            self._total = 0
            self._missing = 0
            self._total_time = 0.0
