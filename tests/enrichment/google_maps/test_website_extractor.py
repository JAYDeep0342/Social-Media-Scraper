import pytest

from app.enrichment.google_maps.website_extractor import WebsiteExtractor
from tests.enrichment.google_maps.fakes import FakeDetailPage


@pytest.mark.asyncio
async def test_extract_returns_href_when_website_present() -> None:
    page = FakeDetailPage(website="https://example-coffee.com")
    extractor = WebsiteExtractor(page)

    assert await extractor.extract() == "https://example-coffee.com"


@pytest.mark.asyncio
async def test_extract_returns_none_when_no_website() -> None:
    page = FakeDetailPage(website=None)
    extractor = WebsiteExtractor(page)

    assert await extractor.extract() is None
