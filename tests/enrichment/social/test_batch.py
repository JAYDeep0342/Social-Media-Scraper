import pytest

from app.enrichment.social.batch import discover_social_links_one
from app.enrichment.social.confidence import Confidence
from app.enrichment.social.link_extractor import LinkCandidate
from app.enrichment.social.metrics import SocialDiscoveryMetrics
from app.models.domain import BusinessLead, SocialLead


class _FakeFetcher:
    def __init__(self, html):
        self.html = html
        self.fetched_urls = []

    async def fetch(self, url):
        self.fetched_urls.append(url)
        return self.html


class _FakeExtractor:
    def __init__(self, candidates):
        self.candidates = candidates

    def extract(self, html):
        return self.candidates


class _FakeFallback:
    def __init__(self, results):
        self.results = results  # dict[platform] -> (url, is_canonical)
        self.calls = []

    async def find(self, business_name, platform):
        self.calls.append((business_name, platform))
        return self.results.get(platform, (None, False))


def _lead(website="https://example.com", instagram=None, facebook=None) -> BusinessLead:
    return BusinessLead(business_name="Test Biz", website=website, social=SocialLead(instagram_url=instagram, facebook_url=facebook))


@pytest.mark.asyncio
async def test_finds_both_on_website_high_confidence() -> None:
    lead = _lead()
    fetcher = _FakeFetcher("<html>irrelevant, extractor is faked</html>")
    extractor = _FakeExtractor(
        [
            LinkCandidate(url="https://www.instagram.com/testbiz", platform="instagram", source="footer"),
            LinkCandidate(url="https://www.facebook.com/testbiz", platform="facebook", source="footer"),
        ]
    )
    fallback = _FakeFallback({})

    result = await discover_social_links_one(lead, fetcher=fetcher, extractor=extractor, fallback=fallback)

    assert result.social.instagram_url == "https://www.instagram.com/testbiz"
    assert result.social.instagram_confidence == Confidence.HIGH.value
    assert result.social.facebook_url == "https://www.facebook.com/testbiz"
    assert result.social.facebook_confidence == Confidence.HIGH.value
    assert fallback.calls == []  # never needed


@pytest.mark.asyncio
async def test_falls_back_to_search_when_website_has_nothing() -> None:
    lead = _lead()
    fetcher = _FakeFetcher("<html>no social links here</html>")
    extractor = _FakeExtractor([])
    fallback = _FakeFallback(
        {
            "instagram": ("https://www.instagram.com/testbiz/", True),
            "facebook": ("https://www.facebook.com/testbiz/posts/1", False),
        }
    )

    result = await discover_social_links_one(lead, fetcher=fetcher, extractor=extractor, fallback=fallback)

    assert result.social.instagram_url == "https://www.instagram.com/testbiz/"
    assert result.social.instagram_confidence == Confidence.MEDIUM.value
    assert result.social.facebook_url == "https://www.facebook.com/testbiz/posts/1"
    assert result.social.facebook_confidence == Confidence.LOW.value


@pytest.mark.asyncio
async def test_skips_website_fetch_when_no_website() -> None:
    lead = _lead(website=None)
    fetcher = _FakeFetcher("<html>should never be used</html>")
    extractor = _FakeExtractor([])
    fallback = _FakeFallback({"instagram": (None, False), "facebook": (None, False)})

    await discover_social_links_one(lead, fetcher=fetcher, extractor=extractor, fallback=fallback)

    assert fetcher.fetched_urls == []


@pytest.mark.asyncio
async def test_leaves_pre_existing_urls_untouched() -> None:
    lead = _lead(instagram="https://www.instagram.com/already-known", facebook=None)
    fetcher = _FakeFetcher("<html></html>")
    extractor = _FakeExtractor(
        [LinkCandidate(url="https://www.facebook.com/testbiz", platform="facebook", source="footer")]
    )
    fallback = _FakeFallback({})

    result = await discover_social_links_one(lead, fetcher=fetcher, extractor=extractor, fallback=fallback)

    assert result.social.instagram_url == "https://www.instagram.com/already-known"
    assert result.social.instagram_confidence is None  # untouched, not re-classified
    assert result.social.facebook_url == "https://www.facebook.com/testbiz"


@pytest.mark.asyncio
async def test_html_fetch_failure_falls_through_to_search() -> None:
    lead = _lead()
    fetcher = _FakeFetcher(None)  # simulates a failed fetch
    extractor = _FakeExtractor([])
    fallback = _FakeFallback({"instagram": ("https://www.instagram.com/testbiz/", True), "facebook": (None, False)})

    result = await discover_social_links_one(lead, fetcher=fetcher, extractor=extractor, fallback=fallback)

    assert result.social.instagram_url == "https://www.instagram.com/testbiz/"


@pytest.mark.asyncio
async def test_metrics_are_recorded() -> None:
    lead = _lead()
    fetcher = _FakeFetcher("<html></html>")
    extractor = _FakeExtractor(
        [LinkCandidate(url="https://www.instagram.com/testbiz", platform="instagram", source="footer")]
    )
    fallback = _FakeFallback({"facebook": ("https://www.facebook.com/testbiz/", True)})
    metrics = SocialDiscoveryMetrics()

    await discover_social_links_one(lead, fetcher=fetcher, extractor=extractor, fallback=fallback, metrics=metrics)

    snapshot = await metrics.snapshot()
    assert snapshot.total_processed == 1
    assert snapshot.html_fetch_success == 1
    assert snapshot.website_success == 1
    assert snapshot.search_fallback_used == 1
    assert snapshot.instagram_found == 1
    assert snapshot.facebook_found == 1
