"""CSV export for benchmark results, so every benchmark run can be
appended to a durable, spreadsheet-friendly file for later comparison."""

import csv
from pathlib import Path
from typing import Iterable, Union

from app.schemas.benchmark import BenchmarkResult

_CSV_FIELDS = [
    "name",
    "execution_time_seconds",
    "cpu_percent",
    "ram_mb",
    "success_count",
    "failure_count",
    "success_rate",
    "started_at",
    "finished_at",
]


def export_benchmark_csv(results: Iterable[BenchmarkResult], path: Union[str, Path]) -> Path:
    """Append one row per BenchmarkResult to `path`, writing a header if the
    file doesn't exist yet. Returns the resolved path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "name": result.name,
                    "execution_time_seconds": result.execution_time_seconds,
                    "cpu_percent": result.cpu_percent,
                    "ram_mb": result.ram_mb,
                    "success_count": result.success_count,
                    "failure_count": result.failure_count,
                    "success_rate": result.success_rate,
                    "started_at": result.started_at.isoformat(),
                    "finished_at": result.finished_at.isoformat(),
                }
            )
    return path
