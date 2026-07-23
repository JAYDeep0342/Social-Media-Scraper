"""Reusable benchmark timer.

Wrap any future block of work in `BenchmarkTimer` to capture execution time,
CPU%, RAM delta, and success/failure counts as a `BenchmarkResult`. Contains
no scraping logic — it is purely a measurement utility. CPU/RAM sampling is
delegated to `app.metrics` so both packages share one measurement source.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from app.benchmark.exporter import export_benchmark_csv
from app.metrics.cpu import get_process_cpu_percent
from app.metrics.ram import get_process_ram_mb
from app.metrics.timer import Stopwatch
from app.schemas.benchmark import BenchmarkResult


class BenchmarkTimer:
    def __init__(self, name: str) -> None:
        self.name = name
        self._success_count = 0
        self._failure_count = 0
        self._started_at: Optional[datetime] = None
        self._stopwatch: Optional[Stopwatch] = None
        self._start_ram_mb: float = 0.0
        self.result: Optional[BenchmarkResult] = None

    def record_success(self, count: int = 1) -> None:
        self._success_count += count

    def record_failure(self, count: int = 1) -> None:
        self._failure_count += count

    def __enter__(self) -> "BenchmarkTimer":
        self._started_at = datetime.now(timezone.utc)
        get_process_cpu_percent()  # prime psutil's internal CPU counter
        self._start_ram_mb = get_process_ram_mb()
        self._stopwatch = Stopwatch()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed = self._stopwatch.elapsed_seconds()
        finished_at = datetime.now(timezone.utc)
        cpu_percent = get_process_cpu_percent()
        end_ram_mb = get_process_ram_mb()

        if exc_type is not None:
            self.record_failure()

        self.result = BenchmarkResult(
            name=self.name,
            execution_time_seconds=elapsed,
            cpu_percent=cpu_percent,
            ram_mb=round(max(end_ram_mb - self._start_ram_mb, 0.0), 2),
            success_count=self._success_count,
            failure_count=self._failure_count,
            started_at=self._started_at,
            finished_at=finished_at,
        )

    def export_csv(self, path: Union[str, Path]) -> Path:
        """Append this run's result to a CSV file. Raises if called before
        the `with` block has exited (i.e. before a result exists)."""
        if self.result is None:
            raise RuntimeError("export_csv() called before the benchmark finished")
        return export_benchmark_csv([self.result], path)
