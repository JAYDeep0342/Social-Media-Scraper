"""Benchmark harness for the full pipeline orchestrator at increasing
batch sizes (10/25/50/100 businesses), reusing the generic
BenchmarkTimer/CSV export infra. Reports both the standard BenchmarkResult
(execution time/success/failure, consistent with every other phase) and
the richer PipelineMetricsSnapshot (which includes stage-wise timings).

Requires real browser/network resources to benchmark live. For fast,
deterministic runs (CI, or isolating orchestration overhead from live
network/browser variance), inject fakes via browser_pool/social_* — same
pattern as every other phase's benchmarks module.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

from app.benchmark.benchmark import BenchmarkTimer
from app.benchmark.exporter import export_benchmark_csv
from app.pipeline.orchestrator import PipelineConcurrency, PipelineOrchestrator
from app.schemas.benchmark import BenchmarkResult
from app.schemas.search import SearchRequest

BENCHMARK_TIERS: Tuple[int, ...] = (10, 25, 50, 100)


@dataclass
class PipelineBenchmarkResult:
    benchmark: BenchmarkResult
    stage_times: dict


async def benchmark_tier(
    limit: int,
    *,
    keyword: str = "coffee shops",
    location: str = "Seattle, WA",
    browser_manager: Optional[Any] = None,
    browser_pool: Optional[Any] = None,
    social_fetcher: Optional[Any] = None,
    social_extractor: Optional[Any] = None,
    social_fallback: Optional[Any] = None,
    concurrency: Optional[PipelineConcurrency] = None,
) -> PipelineBenchmarkResult:
    orchestrator = PipelineOrchestrator(concurrency=concurrency)
    request = SearchRequest(keyword=keyword, location=location, limit=limit)

    with BenchmarkTimer(f"pipeline_{limit}") as timer:
        result = await orchestrator.run(
            request,
            browser_manager=browser_manager,
            browser_pool=browser_pool,
            social_fetcher=social_fetcher,
            social_extractor=social_extractor,
            social_fallback=social_fallback,
        )
        timer.record_success(len(result.leads))
        timer.record_failure(max(0, limit - len(result.leads)))

    return PipelineBenchmarkResult(benchmark=timer.result, stage_times=result.metrics.stage_times)


async def run_benchmarks(
    tiers: Tuple[int, ...] = BENCHMARK_TIERS,
    *,
    keyword: str = "coffee shops",
    location: str = "Seattle, WA",
    browser_manager: Optional[Any] = None,
    browser_pool: Optional[Any] = None,
    social_fetcher: Optional[Any] = None,
    social_extractor: Optional[Any] = None,
    social_fallback: Optional[Any] = None,
    concurrency: Optional[PipelineConcurrency] = None,
    csv_path: Optional[Path] = None,
) -> List[PipelineBenchmarkResult]:
    results: List[PipelineBenchmarkResult] = []
    for limit in tiers:
        result = await benchmark_tier(
            limit,
            keyword=keyword,
            location=location,
            browser_manager=browser_manager,
            browser_pool=browser_pool,
            social_fetcher=social_fetcher,
            social_extractor=social_extractor,
            social_fallback=social_fallback,
            concurrency=concurrency,
        )
        results.append(result)
        if csv_path is not None:
            export_benchmark_csv([result.benchmark], csv_path)
    return results
