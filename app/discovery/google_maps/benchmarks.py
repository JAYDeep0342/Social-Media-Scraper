"""Benchmark harness for the Google Maps discovery engine at increasing
lead-count tiers (10/25/50/100), reusing the generic BenchmarkTimer/CSV
export infra from app.benchmark (Phase 1.1/2).

Requires a real Playwright Page (Chromium with `playwright install
chromium`, network access to google.com) to benchmark live. For CI or
environments without a live browser, pass a fake/mocked Page implementing
the same interface (see tests/discovery/google_maps/fakes.py) — the
pipeline itself doesn't know or care whether the Page is real.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from playwright.async_api import Page

from app.benchmark.benchmark import BenchmarkTimer
from app.benchmark.exporter import export_benchmark_csv
from app.discovery.google_maps.pipeline import run_discovery
from app.schemas.benchmark import BenchmarkResult

BENCHMARK_TIERS: Tuple[int, ...] = (10, 25, 50, 100)


async def benchmark_tier(
    page: Page, *, keyword: str, location: str, limit: int
) -> BenchmarkResult:
    with BenchmarkTimer(f"google_maps_discovery_{limit}") as timer:
        result = await run_discovery(page, keyword=keyword, location=location, limit=limit)
        timer.record_success(len(result.leads))
    return timer.result


async def run_benchmarks(
    page: Page,
    *,
    keyword: str,
    location: str,
    tiers: Tuple[int, ...] = BENCHMARK_TIERS,
    csv_path: Optional[Path] = None,
) -> List[BenchmarkResult]:
    results: List[BenchmarkResult] = []
    for limit in tiers:
        result = await benchmark_tier(page, keyword=keyword, location=location, limit=limit)
        results.append(result)
        if csv_path is not None:
            export_benchmark_csv([result], csv_path)
    return results


if __name__ == "__main__":
    import asyncio

    from app.discovery.google_maps.browser_manager import BrowserManager
    from app.discovery.google_maps.browser_pool import BrowserContextPool

    async def _main() -> None:
        manager = BrowserManager()
        await manager.start()
        pool = BrowserContextPool(manager, pool_size=1)
        await pool.start()

        async with pool.acquire() as page:
            results = await run_benchmarks(
                page,
                keyword="coffee shops",
                location="Seattle, WA",
                csv_path=Path("logs/benchmarks/google_maps.csv"),
            )

        for result in results:
            print(
                f"{result.name}: {result.execution_time_seconds}s, "
                f"{result.success_count} leads, "
                f"{result.success_count / result.execution_time_seconds:.2f} leads/sec"
            )

        await pool.stop()
        await manager.stop()

    asyncio.run(_main())
