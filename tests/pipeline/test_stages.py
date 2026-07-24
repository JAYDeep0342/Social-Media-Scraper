"""Each pipeline stage is tested in isolation here, constructing an
OrchestratorContext directly and calling `stage.process(context)` — no
full PipelineOrchestrator run required, satisfying "each stage should
remain independently testable."
"""

import pytest

from app.enrichment.social.confidence import Confidence
from app.enrichment.social.link_extractor import LinkCandidate
from app.models.domain import BusinessLead, SocialLead
from app.pipeline.orchestrator import (
    MapsDiscoveryStage,
    OrchestratorContext,
    PipelineConcurrency,
    SocialDiscoveryStage,
    UrlSelectionStage,
    WebsiteEnrichmentStage,
)
from tests.pipeline.fakes import (
    FakeCard,
    FakeOrchestratorPage,
    FakeOrchestratorPool,
    FakeSocialExtractor,
    FakeSocialFallback,
    FakeSocialFetcher,
)


def _make_search_request(limit: int = 10):
    from app.schemas.search import SearchRequest

    return SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=limit)


@pytest.mark.asyncio
async def test_maps_discovery_stage_populates_leads() -> None:
    cards = [FakeCard(name=f"Business {i}", maps_url=f"https://maps.google.com/place/{i}/data=!1s0x{i}:0x{i}") for i in range(5)]
    pool = FakeOrchestratorPool([FakeOrchestratorPage(cards=cards, url_to_website={})])
    context = OrchestratorContext(
        request=_make_search_request(limit=5), browser_pool=pool, concurrency=PipelineConcurrency()
    )

    result = await MapsDiscoveryStage().process(context)

    assert len(result.leads) == 5
    assert all(lead.website is None for lead in result.leads)
    assert all(lead.social.google_maps_url for lead in result.leads)
    assert result.progress is None  # not attached in this isolated test


@pytest.mark.asyncio
async def test_website_enrichment_stage_fills_in_websites() -> None:
    leads = [
        BusinessLead(business_name="A", website=None, social=SocialLead(google_maps_url="https://maps.google.com/place/a")),
        BusinessLead(business_name="B", website=None, social=SocialLead(google_maps_url="https://maps.google.com/place/b")),
    ]
    pool = FakeOrchestratorPool(
        [
            FakeOrchestratorPage(
                cards=[],
                url_to_website={
                    "https://maps.google.com/place/a": "https://a-website.example",
                    "https://maps.google.com/place/b": None,
                },
            )
            for _ in range(2)
        ]
    )
    context = OrchestratorContext(request=_make_search_request(), browser_pool=pool, concurrency=PipelineConcurrency())
    context.leads = leads

    result = await WebsiteEnrichmentStage().process(context)

    assert result.leads[0].website == "https://a-website.example"
    assert result.leads[1].website is None


@pytest.mark.asyncio
async def test_social_discovery_stage_fills_in_social_urls() -> None:
    lead = BusinessLead(business_name="A", website="https://a-website.example", social=SocialLead())
    extractor = FakeSocialExtractor(
        {"https://a-website.example": [LinkCandidate(url="https://www.instagram.com/a", platform="instagram", source="footer")]}
    )
    fetcher = FakeSocialFetcher(extractor)
    fallback = FakeSocialFallback()

    context = OrchestratorContext(
        request=_make_search_request(),
        browser_pool=None,
        concurrency=PipelineConcurrency(),
        social_fetcher=fetcher,
        social_extractor=extractor,
        social_fallback=fallback,
    )
    context.leads = [lead]

    result = await SocialDiscoveryStage().process(context)

    assert result.leads[0].social.instagram_url == "https://www.instagram.com/a"
    assert result.leads[0].social.instagram_confidence == "high"


@pytest.mark.asyncio
async def test_url_selection_stage_normalizes_and_cleans() -> None:
    lead = BusinessLead(
        business_name="A",
        website="https://a.example",
        social=SocialLead(
            instagram_url="https://instagram.com/a?igshid=abc",
            instagram_confidence=Confidence.HIGH.value,
        ),
    )
    context = OrchestratorContext(request=_make_search_request(), browser_pool=None, concurrency=PipelineConcurrency())
    context.leads = [lead]

    result = await UrlSelectionStage().process(context)

    assert result.leads[0].social.instagram_url == "https://www.instagram.com/a"


@pytest.mark.asyncio
async def test_url_selection_stage_drops_malformed_urls() -> None:
    lead = BusinessLead(
        business_name="A",
        website=None,
        social=SocialLead(facebook_url="not a url", facebook_confidence=Confidence.LOW.value),
    )
    context = OrchestratorContext(request=_make_search_request(), browser_pool=None, concurrency=PipelineConcurrency())
    context.leads = [lead]

    result = await UrlSelectionStage().process(context)

    assert result.leads[0].social.facebook_url is None
    assert result.leads[0].social.facebook_confidence is None


@pytest.mark.asyncio
async def test_url_selection_stage_is_a_noop_for_leads_without_social_urls() -> None:
    lead = BusinessLead(business_name="A", website=None, social=SocialLead())
    context = OrchestratorContext(request=_make_search_request(), browser_pool=None, concurrency=PipelineConcurrency())
    context.leads = [lead]

    result = await UrlSelectionStage().process(context)

    assert result.leads[0].social.instagram_url is None
    assert result.leads[0].social.facebook_url is None
