import pytest

from app.enrichment.google_maps.benchmarks import BENCHMARK_TIERS, run_benchmarks
from app.models.domain import BusinessLead, SocialLead
from tests.enrichment.google_maps.fakes import FakeDetailPage, FakePool


def _leads(n: int):
    return [
        BusinessLead(
            business_name=f"Business {i}",
            website=None,
            social=SocialLead(google_maps_url=f"https://maps.google.com/place/{i}/data=!1s0x{i}:0x{i}"),
        )
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_run_benchmarks_produces_one_result_per_batch(tmp_path) -> None:
    batch_10 = _leads(10)
    batch_25 = _leads(25)
    url_to_website = {
        lead.social.google_maps_url: f"https://site-{i}.com"
        for i, lead in enumerate([*batch_10, *batch_25])
    }
    pool = FakePool([FakeDetailPage(url_to_website=url_to_website) for _ in range(4)])
    csv_path = tmp_path / "enrichment_benchmarks.csv"

    results = await run_benchmarks(pool, [batch_10, batch_25], csv_path=csv_path)

    assert [r.success_count for r in results] == [10, 25]
    assert all(r.execution_time_seconds >= 0 for r in results)
    assert csv_path.exists()


@pytest.mark.asyncio
async def test_default_tiers_are_10_25_50_100() -> None:
    assert BENCHMARK_TIERS == (10, 25, 50, 100)
