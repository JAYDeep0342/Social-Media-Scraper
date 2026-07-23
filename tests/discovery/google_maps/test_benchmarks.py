import pytest

from app.discovery.google_maps.benchmarks import BENCHMARK_TIERS, run_benchmarks
from tests.discovery.google_maps.fakes import FakeCard, FakePage


def _cards(n: int):
    return [
        FakeCard(name=f"Business {i}", maps_url=f"https://maps.google.com/place/{i}/data=!1s0x{i}:0x{i}")
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_run_benchmarks_produces_one_result_per_tier(tmp_path) -> None:
    page = FakePage(cards=_cards(120), reveal_schedule=[120])
    csv_path = tmp_path / "benchmarks.csv"

    results = await run_benchmarks(
        page, keyword="coffee shops", location="Seattle, WA", tiers=(10, 25), csv_path=csv_path
    )

    assert [r.success_count for r in results] == [10, 25]
    assert all(r.execution_time_seconds >= 0 for r in results)
    assert csv_path.exists()

    import csv as csv_module

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv_module.DictReader(f))
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_default_tiers_are_10_25_50_100() -> None:
    assert BENCHMARK_TIERS == (10, 25, 50, 100)
