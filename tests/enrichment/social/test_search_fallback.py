import pytest

from app.enrichment.social.search_fallback import SocialSearchFallback


class _FakeProvider:
    def __init__(self, urls):
        self.urls = urls
        self.last_query = None

    async def discover(self, keyword, location, limit):
        self.last_query = keyword
        return self.urls[:limit]


@pytest.mark.asyncio
async def test_finds_canonical_related_result_as_medium_confidence() -> None:
    provider = _FakeProvider(
        [
            "https://www.instagram.com/starbucks/reels/",  # non-canonical, would be skipped in pass 1
            "https://www.instagram.com/starbucks/",  # canonical + related -> should win
            "https://www.instagram.com/staryucksfake/",  # canonical but unrelated (typosquat)
        ]
    )
    fallback = SocialSearchFallback(provider=provider)

    url, is_canonical = await fallback.find("Starbucks", "instagram")

    assert url == "https://www.instagram.com/starbucks"
    assert is_canonical is True


@pytest.mark.asyncio
async def test_filters_out_ad_junk_targeting_other_domains() -> None:
    provider = _FakeProvider(
        [
            "https://duckduckgo.com/y.js?ad_domain=amazon.com",  # ad junk, not instagram at all
            "https://www.instagram.com/starbucks/",
        ]
    )
    fallback = SocialSearchFallback(provider=provider)

    url, is_canonical = await fallback.find("Starbucks", "instagram")

    assert url == "https://www.instagram.com/starbucks"


@pytest.mark.asyncio
async def test_falls_back_to_non_canonical_result_as_low_confidence() -> None:
    provider = _FakeProvider(["https://www.instagram.com/starbucks/reels/"])
    fallback = SocialSearchFallback(provider=provider)

    url, is_canonical = await fallback.find("Starbucks", "instagram")

    assert url == "https://www.instagram.com/starbucks/reels"
    assert is_canonical is False


@pytest.mark.asyncio
async def test_returns_none_when_no_results() -> None:
    provider = _FakeProvider([])
    fallback = SocialSearchFallback(provider=provider)

    url, is_canonical = await fallback.find("Starbucks", "instagram")

    assert url is None
    assert is_canonical is False


@pytest.mark.asyncio
async def test_query_uses_site_search_syntax() -> None:
    provider = _FakeProvider([])
    fallback = SocialSearchFallback(provider=provider)

    await fallback.find("Joe's Coffee", "facebook")

    assert provider.last_query == 'site:facebook.com "Joe\'s Coffee"'


@pytest.mark.asyncio
async def test_unrelated_typosquat_alone_is_treated_as_weak_signal() -> None:
    """No related canonical match exists, but a canonical-shaped
    (unrelated) result is still returned as a last-resort LOW-confidence
    signal rather than nothing at all."""
    provider = _FakeProvider(["https://www.instagram.com/staryucksfake/"])
    fallback = SocialSearchFallback(provider=provider)

    url, is_canonical = await fallback.find("Starbucks", "instagram")

    assert url == "https://www.instagram.com/staryucksfake"
    assert is_canonical is False
