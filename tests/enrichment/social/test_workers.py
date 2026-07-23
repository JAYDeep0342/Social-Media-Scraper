import pytest

from app.enrichment.social.link_extractor import LinkCandidate
from app.enrichment.social.metrics import SocialDiscoveryMetrics
from app.enrichment.social.workers import discover_social_batch
from app.models.domain import BusinessLead, SocialLead


class _FakeFetcher:
    async def fetch(self, url):
        return "<html></html>"


class _FakeExtractorByUrl:
    """Returns different candidates depending on which website URL was
    fetched, and can simulate a failure for a specific URL."""

    def __init__(self, by_website, fail_websites=None):
        self.by_website = by_website
        self.fail_websites = fail_websites or set()
        self._last_html = None

    def extract(self, html):
        return self._last_html or []


class _FakeFetcherByUrl:
    def __init__(self, extractor, fail_websites=None):
        self._extractor = extractor
        self.fail_websites = fail_websites or set()

    async def fetch(self, url):
        if url in self.fail_websites:
            raise RuntimeError(f"simulated fetch failure for {url}")
        self._extractor._last_html = self._extractor.by_website.get(url, [])
        return "<html></html>"


class _FakeFallback:
    async def find(self, business_name, platform):
        return None, False


def _lead(name, website) -> BusinessLead:
    return BusinessLead(business_name=name, website=website, social=SocialLead())


@pytest.mark.asyncio
async def test_only_leads_missing_social_are_processed() -> None:
    already_complete = BusinessLead(
        business_name="Complete",
        website="https://complete.example",
        social=SocialLead(instagram_url="https://www.instagram.com/complete", facebook_url="https://www.facebook.com/complete"),
    )
    needs_it = _lead("Needs It", "https://needsit.example")

    extractor = _FakeExtractorByUrl(
        {"https://needsit.example": [LinkCandidate(url="https://www.instagram.com/needsit", platform="instagram", source="footer")]}
    )
    fetcher = _FakeFetcherByUrl(extractor)
    fallback = _FakeFallback()

    result = await discover_social_batch([already_complete, needs_it], fetcher=fetcher, extractor=extractor, fallback=fallback)

    assert result[0].social.instagram_url == "https://www.instagram.com/complete"  # untouched
    assert result[1].social.instagram_url == "https://www.instagram.com/needsit"  # newly found


@pytest.mark.asyncio
async def test_returns_same_list_instance_mutated_in_place() -> None:
    leads = [_lead("A", "https://a.example")]
    extractor = _FakeExtractorByUrl({"https://a.example": []})
    fetcher = _FakeFetcherByUrl(extractor)
    fallback = _FakeFallback()

    result = await discover_social_batch(leads, fetcher=fetcher, extractor=extractor, fallback=fallback)

    assert result is leads


@pytest.mark.asyncio
async def test_a_failing_lead_does_not_abort_the_whole_batch() -> None:
    ok_lead = _lead("OK", "https://ok.example")
    failing_lead = _lead("Failing", "https://failing.example")
    good_lead = _lead("Good", "https://good.example")

    extractor = _FakeExtractorByUrl(
        {
            "https://ok.example": [LinkCandidate(url="https://www.instagram.com/ok", platform="instagram", source="footer")],
            "https://good.example": [LinkCandidate(url="https://www.instagram.com/good", platform="instagram", source="footer")],
        }
    )
    fetcher = _FakeFetcherByUrl(extractor, fail_websites={"https://failing.example"})
    fallback = _FakeFallback()

    result = await discover_social_batch(
        [ok_lead, failing_lead, good_lead], fetcher=fetcher, extractor=extractor, fallback=fallback
    )

    assert result[0].social.instagram_url == "https://www.instagram.com/ok"
    assert result[1].social.instagram_url is None  # failed, left as None
    assert result[2].social.instagram_url == "https://www.instagram.com/good"


@pytest.mark.asyncio
async def test_concurrency_with_multiple_leads() -> None:
    leads = [_lead(f"Biz {i}", f"https://biz{i}.example") for i in range(6)]
    extractor = _FakeExtractorByUrl(
        {f"https://biz{i}.example": [LinkCandidate(url=f"https://www.instagram.com/biz{i}", platform="instagram", source="footer")] for i in range(6)}
    )
    fetcher = _FakeFetcherByUrl(extractor)
    fallback = _FakeFallback()

    result = await discover_social_batch(leads, worker_count=3, fetcher=fetcher, extractor=extractor, fallback=fallback)

    for i, lead in enumerate(result):
        assert lead.social.instagram_url == f"https://www.instagram.com/biz{i}"


@pytest.mark.asyncio
async def test_metrics_reflect_only_processed_leads() -> None:
    already_complete = BusinessLead(
        business_name="Complete",
        website="https://complete.example",
        social=SocialLead(instagram_url="https://www.instagram.com/complete", facebook_url="https://www.facebook.com/complete"),
    )
    needs_it = _lead("Needs It", "https://needsit.example")

    extractor = _FakeExtractorByUrl({"https://needsit.example": []})
    fetcher = _FakeFetcherByUrl(extractor)
    fallback = _FakeFallback()
    metrics = SocialDiscoveryMetrics()

    await discover_social_batch(
        [already_complete, needs_it], fetcher=fetcher, extractor=extractor, fallback=fallback, metrics=metrics
    )

    snapshot = await metrics.snapshot()
    assert snapshot.total_processed == 1  # only "needs_it" was actually processed
