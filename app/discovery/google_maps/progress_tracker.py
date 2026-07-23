"""Tracks discovery progress: cards collected so far, how many remain to
reach the target limit, elapsed time, and throughput (cards/sec)."""

import time
from dataclasses import dataclass


@dataclass
class ProgressSnapshot:
    collected: int
    remaining: int
    elapsed_seconds: float
    cards_per_second: float


class ProgressTracker:
    def __init__(self, target_limit: int) -> None:
        self._target_limit = target_limit
        self._collected = 0
        self._start = time.perf_counter()

    def update(self, collected: int) -> None:
        self._collected = collected

    def snapshot(self) -> ProgressSnapshot:
        elapsed = time.perf_counter() - self._start
        rate = self._collected / elapsed if elapsed > 0 else 0.0
        remaining = max(self._target_limit - self._collected, 0)
        return ProgressSnapshot(
            collected=self._collected,
            remaining=remaining,
            elapsed_seconds=round(elapsed, 3),
            cards_per_second=round(rate, 2),
        )
