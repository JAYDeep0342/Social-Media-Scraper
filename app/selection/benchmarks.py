"""Benchmark harness for the selection engine at increasing batch sizes
(10/25/50/100/1000 businesses), reusing the generic BenchmarkTimer/CSV
export infra from app.benchmark (Phase 1.1/2).

Unlike every prior phase's benchmarks, these are always real runs, never
mocked — this engine performs no I/O at all, so there is nothing to
isolate from network/browser variance.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from app.benchmark.benchmark import BenchmarkTimer
from app.benchmark.exporter import export_benchmark_csv
from app.schemas.benchmark import BenchmarkResult
from app.selection.candidate import Candidate
from app.selection.engine import SelectionEngine
from app.selection.metrics import SelectionMetrics

BENCHMARK_TIERS: Tuple[int, ...] = (10, 25, 50, 100, 1000)


def benchmark_tier(businesses: List[List[Candidate]]) -> BenchmarkResult:
    engine = SelectionEngine()
    metrics = SelectionMetrics()

    with BenchmarkTimer(f"url_selection_{len(businesses)}") as timer:
        selected_count = 0
        for candidates in businesses:
            result = engine.select(candidates, metrics=metrics)
            if result.instagram_url or result.facebook_url:
                selected_count += 1
        timer.record_success(selected_count)
        timer.record_failure(len(businesses) - selected_count)

    return timer.result


def run_benchmarks(
    business_batches: List[List[List[Candidate]]], *, csv_path: Optional[Path] = None
) -> List[BenchmarkResult]:
    results: List[BenchmarkResult] = []
    for batch in business_batches:
        result = benchmark_tier(batch)
        results.append(result)
        if csv_path is not None:
            export_benchmark_csv([result], csv_path)
    return results
