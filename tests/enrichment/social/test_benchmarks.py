import pytest

from app.enrichment.social.benchmarks import BENCHMARK_TIERS, run_benchmarks
from app.models.domain import BusinessLead, SocialLead


class _InstantFetcher:
    async def fetch(self, url):
        return "<html></html>"


class _NoOpExtractor:
    def extract(self, html):
        return []


class _AlwaysFindsFallback:
    async def find(self, business_name, platform):
        return f"https://www.{platform}.com/{business_name.replace(' ', '').lower()}/", True


def _leads(n: int):
    return [BusinessLead(business_name=f"Business{i}", website=f"https://biz{i}.example", social=SocialLead()) for i in range(n)]


@pytest.mark.asyncio
async def test_run_benchmarks_produces_one_result_per_batch(tmp_path, monkeypatch) -> None:
    import app.enrichment.social.workers as workers_module

    async def fake_discover_social_batch(leads, *, worker_count=None, **kwargs):
        for lead in leads:
            lead.social.instagram_url = f"https://www.instagram.com/{lead.business_name.lower()}/"
        return leads

    monkeypatch.setattr(workers_module, "discover_social_batch", fake_discover_social_batch)

    # benchmarks.py imported the function by name, so patch it there too
    import app.enrichment.social.benchmarks as benchmarks_module

    monkeypatch.setattr(benchmarks_module, "discover_social_batch", fake_discover_social_batch)

    csv_path = tmp_path / "social_benchmarks.csv"
    results = await run_benchmarks([_leads(10), _leads(25)], csv_path=csv_path)

    assert [r.success_count for r in results] == [10, 25]
    assert csv_path.exists()


@pytest.mark.asyncio
async def test_default_tiers_are_10_25_50_100() -> None:
    assert BENCHMARK_TIERS == (10, 25, 50, 100)
