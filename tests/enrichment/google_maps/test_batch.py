import pytest

from app.enrichment.google_maps.batch import enrich_one
from app.enrichment.google_maps.cache import EnrichmentCache
from app.models.domain import BusinessLead, SocialLead
from tests.enrichment.google_maps.fakes import FakeDetailPage, FakePool

_MAPS_URL = "https://maps.google.com/place/A/data=!1s0x1:0x1"


@pytest.mark.asyncio
async def test_enriches_lead_missing_website() -> None:
    lead = BusinessLead(business_name="A", website=None, social=SocialLead(google_maps_url=_MAPS_URL))
    pool = FakePool([FakeDetailPage(url_to_website={_MAPS_URL: "https://a.com"})])

    result = await enrich_one(pool, lead)

    assert result.website == "https://a.com"
    assert result is lead  # mutated in place


@pytest.mark.asyncio
async def test_leaves_lead_with_existing_website_untouched() -> None:
    lead = BusinessLead(business_name="A", website="https://already-known.com", social=SocialLead(google_maps_url=_MAPS_URL))
    page = FakeDetailPage(url_to_website={_MAPS_URL: "https://different.com"})
    pool = FakePool([page])

    result = await enrich_one(pool, lead)

    assert result.website == "https://already-known.com"
    assert page.calls == []  # never touched the browser


@pytest.mark.asyncio
async def test_lead_without_maps_url_is_left_untouched() -> None:
    lead = BusinessLead(business_name="A", website=None, social=SocialLead(google_maps_url=None))
    pool = FakePool([FakeDetailPage()])

    result = await enrich_one(pool, lead)

    assert result.website is None


@pytest.mark.asyncio
async def test_confirmed_no_website_sets_none() -> None:
    lead = BusinessLead(business_name="A", website=None, social=SocialLead(google_maps_url=_MAPS_URL))
    pool = FakePool([FakeDetailPage(url_to_website={_MAPS_URL: None})])

    result = await enrich_one(pool, lead)

    assert result.website is None


@pytest.mark.asyncio
async def test_cache_hit_skips_browser_and_uses_cached_value() -> None:
    lead = BusinessLead(business_name="A", website=None, social=SocialLead(google_maps_url=_MAPS_URL))
    cache = EnrichmentCache()
    await cache.set(_MAPS_URL, "https://cached.com")

    page = FakeDetailPage(url_to_website={_MAPS_URL: "https://should-not-be-used.com"})
    pool = FakePool([page])

    result = await enrich_one(pool, lead, cache=cache)

    assert result.website == "https://cached.com"
    assert page.calls == []  # never touched the browser


@pytest.mark.asyncio
async def test_cache_is_populated_after_a_real_lookup() -> None:
    lead = BusinessLead(business_name="A", website=None, social=SocialLead(google_maps_url=_MAPS_URL))
    cache = EnrichmentCache()
    pool = FakePool([FakeDetailPage(url_to_website={_MAPS_URL: "https://a.com"})])

    await enrich_one(pool, lead, cache=cache)

    cached = await cache.get(_MAPS_URL)
    assert cached is not None
    assert cached.website == "https://a.com"
