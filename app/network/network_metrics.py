"""Aggregate networking metrics: request counts, latency, retries, and
open-connection tracking, for the whole life of a SessionManager.

Distinct from `app.metrics` (process-wide CPU/RAM helpers) and
`app.benchmark` (per-run CPU/RAM/success/failure) — this is specific to the
network layer's own request lifecycle.
"""

import asyncio
import time
from dataclasses import dataclass


@dataclass
class NetworkMetricsSnapshot:
    total_requests: int
    successful_requests: int
    failed_requests: int
    retry_count: int
    average_latency_ms: float
    open_connections: int


class NetworkMetrics:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._retry_count = 0
        self._total_latency_ms = 0.0
        self._open_connections = 0

    async def record_request_start(self) -> float:
        async with self._lock:
            self._open_connections += 1
        return time.perf_counter()

    async def record_request_end(self, start_time: float, *, success: bool) -> None:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        async with self._lock:
            self._open_connections = max(0, self._open_connections - 1)
            self._total_requests += 1
            self._total_latency_ms += elapsed_ms
            if success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1

    async def record_retry(self) -> None:
        async with self._lock:
            self._retry_count += 1

    async def snapshot(self) -> NetworkMetricsSnapshot:
        async with self._lock:
            avg_latency = self._total_latency_ms / self._total_requests if self._total_requests else 0.0
            return NetworkMetricsSnapshot(
                total_requests=self._total_requests,
                successful_requests=self._successful_requests,
                failed_requests=self._failed_requests,
                retry_count=self._retry_count,
                average_latency_ms=round(avg_latency, 2),
                open_connections=self._open_connections,
            )

    async def reset(self) -> None:
        async with self._lock:
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._retry_count = 0
            self._total_latency_ms = 0.0
            self._open_connections = 0
