"""Benchmark harness for website enrichment at increasing batch sizes
(10/25/50/100), reusing the generic BenchmarkTimer/CSV export infra from
app.benchmark (Phase 1.1/2) — same pattern as
app.discovery.google_maps.benchmarks (Phase 3).

Requires real BusinessLead objects with valid, missing-website entries and
a started BrowserContextPool to benchmark live. For CI or environments
without a live browser, pass leads whose Maps URLs point at a fake/mocked
page (see tests/enrichment/google_maps/fakes.py).
"""

from pathlib import Path
from typing import List, Optional, Tuple

from app.benchmark.benchmark import BenchmarkTimer
from app.benchmark.exporter import export_benchmark_csv
from app.discovery.google_maps.browser_pool import BrowserContextPool
from app.enrichment.google_maps.workers import enrich_batch
from app.models.domain import BusinessLead
from app.network.retry_strategy import RetryPolicy
from app.schemas.benchmark import BenchmarkResult

BENCHMARK_TIERS: Tuple[int, ...] = (10, 25, 50, 100)


async def benchmark_tier(
    pool: BrowserContextPool,
    leads: List[BusinessLead],
    *,
    worker_count: Optional[int] = None,
    retry_policy: Optional[RetryPolicy] = None,
) -> BenchmarkResult:
    with BenchmarkTimer(f"website_enrichment_{len(leads)}") as timer:
        enriched = await enrich_batch(pool, leads, worker_count=worker_count, retry_policy=retry_policy)
        success_count = sum(1 for lead in enriched if lead.website)
        timer.record_success(success_count)
        timer.record_failure(len(enriched) - success_count)
    return timer.result


async def run_benchmarks(
    pool: BrowserContextPool,
    lead_batches: List[List[BusinessLead]],
    *,
    worker_count: Optional[int] = None,
    retry_policy: Optional[RetryPolicy] = None,
    csv_path: Optional[Path] = None,
) -> List[BenchmarkResult]:
    results: List[BenchmarkResult] = []
    for batch in lead_batches:
        result = await benchmark_tier(pool, batch, worker_count=worker_count, retry_policy=retry_policy)
        results.append(result)
        if csv_path is not None:
            export_benchmark_csv([result], csv_path)
    return results
