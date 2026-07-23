"""Reusable, on-demand CPU/RAM/elapsed-time snapshot collector.

Unlike `app.benchmark.BenchmarkTimer` (which measures one bounded block and
tracks success/failure counts), `MetricsCollector` can be polled repeatedly
over the lifetime of a long-running task.
"""

from dataclasses import dataclass

from app.metrics.cpu import get_process_cpu_percent
from app.metrics.ram import get_process_ram_mb
from app.metrics.timer import Stopwatch


@dataclass
class MetricsSnapshot:
    elapsed_seconds: float
    cpu_percent: float
    ram_mb: float


class MetricsCollector:
    def __init__(self) -> None:
        self._stopwatch = Stopwatch()
        get_process_cpu_percent()  # prime psutil's internal CPU counter

    def snapshot(self) -> MetricsSnapshot:
        return MetricsSnapshot(
            elapsed_seconds=self._stopwatch.elapsed_seconds(),
            cpu_percent=get_process_cpu_percent(),
            ram_mb=get_process_ram_mb(),
        )

    def reset(self) -> None:
        self._stopwatch.reset()
