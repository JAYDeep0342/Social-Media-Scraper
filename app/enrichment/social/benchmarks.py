"""Benchmark harness for social discovery at increasing batch sizes
(10/25/50/100), reusing the generic BenchmarkTimer/CSV export infra from
app.benchmark (Phase 1.1/2) — same pattern as
app.discovery.google_maps.benchmarks (Phase 3) and
app.enrichment.google_maps.benchmarks (Phase 4).
"""

from pathlib import Path
from typing import List, Optional, Tuple

from app.benchmark.benchmark import BenchmarkTimer
from app.benchmark.exporter import export_benchmark_csv
from app.enrichment.social.workers import discover_social_batch
from app.models.domain import BusinessLead
from app.schemas.benchmark import BenchmarkResult

BENCHMARK_TIERS: Tuple[int, ...] = (10, 25, 50, 100)


async def benchmark_tier(leads: List[BusinessLead], *, worker_count: Optional[int] = None) -> BenchmarkResult:
    with BenchmarkTimer(f"social_discovery_{len(leads)}") as timer:
        enriched = await discover_social_batch(leads, worker_count=worker_count)
        success_count = sum(1 for lead in enriched if lead.social.instagram_url or lead.social.facebook_url)
        timer.record_success(success_count)
        timer.record_failure(len(enriched) - success_count)
    return timer.result


async def run_benchmarks(
    lead_batches: List[List[BusinessLead]],
    *,
    worker_count: Optional[int] = None,
    csv_path: Optional[Path] = None,
) -> List[BenchmarkResult]:
    results: List[BenchmarkResult] = []
    for batch in lead_batches:
        result = await benchmark_tier(batch, worker_count=worker_count)
        results.append(result)
        if csv_path is not None:
            export_benchmark_csv([result], csv_path)
    return results
