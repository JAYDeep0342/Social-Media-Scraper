import pytest

from app.enrichment.google_maps.cache import EnrichmentCache

_URL = "https://www.google.com/maps/place/A/data=!4m7!3m6!1s0x54906ab2f0c61d05:0x771b2a7dce963d58!8m2"
_URL_DIFFERENT_QUERY = _URL + "?authuser=1&hl=en"


@pytest.mark.asyncio
async def test_miss_returns_none() -> None:
    cache = EnrichmentCache()
    assert await cache.get(_URL) is None
    assert await cache.has(_URL) is False


@pytest.mark.asyncio
async def test_set_and_get_roundtrip_with_website() -> None:
    cache = EnrichmentCache()
    await cache.set(_URL, "https://example.com")

    cached = await cache.get(_URL)
    assert cached is not None
    assert cached.website == "https://example.com"


@pytest.mark.asyncio
async def test_confirmed_no_website_is_still_a_cache_hit() -> None:
    """The key correctness property: caching 'no website' must be
    distinguishable from 'never checked'."""
    cache = EnrichmentCache()
    await cache.set(_URL, None)

    cached = await cache.get(_URL)
    assert cached is not None
    assert cached.website is None
    assert await cache.has(_URL) is True


@pytest.mark.asyncio
async def test_same_place_different_query_string_hits_same_cache_entry() -> None:
    cache = EnrichmentCache()
    await cache.set(_URL, "https://example.com")

    cached = await cache.get(_URL_DIFFERENT_QUERY)
    assert cached is not None
    assert cached.website == "https://example.com"
