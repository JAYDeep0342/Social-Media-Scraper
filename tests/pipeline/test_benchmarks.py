import pytest

from app.pipeline.benchmarks import BENCHMARK_TIERS
from tests.pipeline.test_orchestrator import _build_fake_pool, _build_fake_social


@pytest.mark.asyncio
async def test_run_benchmarks_produces_one_result_per_tier(tmp_path) -> None:
    tiers = (5, 8)
    csv_path = tmp_path / "pipeline_benchmarks.csv"

    results = []
    for limit in tiers:
        pool = _build_fake_pool(limit)
        fetcher, extractor, fallback = _build_fake_social(limit)
        from app.pipeline.benchmarks import benchmark_tier

        result = await benchmark_tier(
            limit, browser_pool=pool, social_fetcher=fetcher, social_extractor=extractor, social_fallback=fallback
        )
        results.append(result)
        from app.benchmark.exporter import export_benchmark_csv

        export_benchmark_csv([result.benchmark], csv_path)

    assert [r.benchmark.success_count for r in results] == [5, 8]
    assert all(set(r.stage_times.keys()) == {"maps_discovery", "website_enrichment", "social_discovery", "url_selection"} for r in results)
    assert csv_path.exists()


@pytest.mark.asyncio
async def test_default_tiers_are_10_25_50_100() -> None:
    assert BENCHMARK_TIERS == (10, 25, 50, 100)
