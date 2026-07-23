import pytest

from app.enrichment.google_maps.metrics import EnrichmentMetrics
from app.enrichment.google_maps.workers import enrich_batch
from app.exceptions.errors import ExtractionError, ScraperTimeoutError
from app.models.domain import BusinessLead, SocialLead
from app.network.retry_strategy import RetryPolicy
from tests.enrichment.google_maps.fakes import FakeDetailPage, FakePool

_FAST_RETRY_POLICY = RetryPolicy(
    max_attempts=2, base_delay=0.01, max_delay=0.02, jitter=0.0, retryable_exceptions=(ScraperTimeoutError, ExtractionError)
)


def _lead(i: int, *, website=None) -> BusinessLead:
    return BusinessLead(
        business_name=f"Business {i}",
        website=website,
        social=SocialLead(google_maps_url=f"https://maps.google.com/place/{i}/data=!1s0x{i}:0x{i}"),
    )


@pytest.mark.asyncio
async def test_only_leads_missing_website_are_processed() -> None:
    already_has_website = _lead(0, website="https://existing.com")
    needs_enrichment = _lead(1)

    url_to_website = {needs_enrichment.social.google_maps_url: "https://found.com"}
    pool = FakePool([FakeDetailPage(url_to_website=url_to_website) for _ in range(2)])

    result = await enrich_batch(pool, [already_has_website, needs_enrichment])

    assert result[0].website == "https://existing.com"  # untouched
    assert result[1].website == "https://found.com"  # enriched


@pytest.mark.asyncio
async def test_returns_same_list_instance_with_leads_mutated_in_place() -> None:
    leads = [_lead(0)]
    url_to_website = {leads[0].social.google_maps_url: "https://a.com"}
    pool = FakePool([FakeDetailPage(url_to_website=url_to_website)])

    result = await enrich_batch(pool, leads)

    assert result is leads
    assert leads[0].website == "https://a.com"


@pytest.mark.asyncio
async def test_workers_process_multiple_leads_concurrently_with_bounded_pool() -> None:
    leads = [_lead(i) for i in range(6)]
    url_to_website = {lead.social.google_maps_url: f"https://site-{i}.com" for i, lead in enumerate(leads)}
    pool = FakePool([FakeDetailPage(url_to_website=url_to_website) for _ in range(2)])  # pool smaller than batch

    result = await enrich_batch(pool, leads, worker_count=4)

    for i, lead in enumerate(result):
        assert lead.website == f"https://site-{i}.com"


@pytest.mark.asyncio
async def test_a_failing_lead_does_not_abort_the_whole_batch() -> None:
    ok_lead = _lead(0)
    failing_lead = _lead(1)
    good_lead = _lead(2)

    url_to_website = {
        ok_lead.social.google_maps_url: "https://ok.com",
        good_lead.social.google_maps_url: "https://good.com",
    }
    fail_urls = {failing_lead.social.google_maps_url}
    pool = FakePool([FakeDetailPage(url_to_website=url_to_website, fail_urls=fail_urls) for _ in range(2)])

    result = await enrich_batch(pool, [ok_lead, failing_lead, good_lead], retry_policy=_FAST_RETRY_POLICY)

    assert result[0].website == "https://ok.com"
    assert result[1].website is None  # failed after retries, left as None
    assert result[2].website == "https://good.com"


@pytest.mark.asyncio
async def test_metrics_reflect_only_processed_leads() -> None:
    already_has_website = _lead(0, website="https://existing.com")
    found = _lead(1)
    missing = _lead(2)

    url_to_website = {found.social.google_maps_url: "https://found.com", missing.social.google_maps_url: None}
    pool = FakePool([FakeDetailPage(url_to_website=url_to_website) for _ in range(2)])
    metrics = EnrichmentMetrics()

    await enrich_batch(pool, [already_has_website, found, missing], metrics=metrics)

    snapshot = await metrics.snapshot()
    assert snapshot.total_enriched == 2  # the pre-existing website lead was never touched
    assert snapshot.missing_websites == 1
    assert snapshot.success_rate == 50.0
