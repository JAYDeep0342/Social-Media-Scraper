import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.enrichment.social.link_extractor import LinkCandidate
from app.pipeline.orchestrator import PipelineConcurrency, PipelineOrchestrator
from app.schemas.search import SearchRequest
from tests.pipeline.fakes import (
    FakeCard,
    FakeOrchestratorPage,
    FakeOrchestratorPool,
    FakeSocialExtractor,
    FakeSocialFallback,
    FakeSocialFetcher,
)


def _build_fake_pool(n_businesses: int, *, with_websites: bool = True, pool_size: int = 3):
    cards = [FakeCard(name=f"Business {i}", maps_url=f"https://maps.google.com/place/{i}/data=!1s0x{i}:0x{i}") for i in range(n_businesses)]
    url_to_website = {
        card.maps_url: (f"https://biz{i}.example" if with_websites else None) for i, card in enumerate(cards)
    }
    pages = [FakeOrchestratorPage(cards=cards, url_to_website=url_to_website) for _ in range(pool_size)]
    return FakeOrchestratorPool(pages)


def _build_fake_social(n_businesses: int):
    candidates_by_website = {
        f"https://biz{i}.example": [
            LinkCandidate(url=f"https://www.instagram.com/biz{i}", platform="instagram", source="footer")
        ]
        for i in range(n_businesses)
    }
    extractor = FakeSocialExtractor(candidates_by_website)
    fetcher = FakeSocialFetcher(extractor)
    fallback = FakeSocialFallback()
    return fetcher, extractor, fallback


@pytest.mark.asyncio
async def test_full_pipeline_runs_all_four_stages_end_to_end() -> None:
    pool = _build_fake_pool(5)
    fetcher, extractor, fallback = _build_fake_social(5)

    orchestrator = PipelineOrchestrator()
    request = SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=5)

    result = await orchestrator.run(
        request, browser_pool=pool, social_fetcher=fetcher, social_extractor=extractor, social_fallback=fallback
    )

    assert len(result.leads) == 5
    for i, lead in enumerate(result.leads):
        assert lead.website == f"https://biz{i}.example"
        assert lead.social.instagram_url == f"https://www.instagram.com/biz{i}"
        assert lead.social.instagram_confidence == "high"


@pytest.mark.asyncio
async def test_progress_and_metrics_are_populated() -> None:
    pool = _build_fake_pool(4)
    fetcher, extractor, fallback = _build_fake_social(4)
    orchestrator = PipelineOrchestrator()
    request = SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=4)

    result = await orchestrator.run(
        request, browser_pool=pool, social_fetcher=fetcher, social_extractor=extractor, social_fallback=fallback
    )

    assert result.progress.current_stage == "url_selection"
    assert result.progress.elapsed_seconds >= 0
    assert set(result.metrics.stage_times.keys()) == {
        "maps_discovery",
        "website_enrichment",
        "social_discovery",
        "url_selection",
    }
    assert result.metrics.success_rate == 100.0  # every business got website + instagram


@pytest.mark.asyncio
async def test_enrichment_worker_count_bounds_concurrent_enrichment(monkeypatch) -> None:
    """PipelineConcurrency.enrichment_worker_count must cap how many
    enrich_one calls the streaming pipeline runs concurrently -- verified
    by measuring the maximum number ever in flight at once, which can
    only reach N if N enrichment workers are truly running concurrently.
    Social discovery is kept instant here so it never becomes the
    bottleneck limiting how many leads reach enrichment's queue at once.
    """
    import app.pipeline.orchestrator as orchestrator_module

    in_flight = 0
    max_in_flight = 0

    async def fake_enrich_one(pool, lead, **kwargs):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return lead

    async def instant_discover_social_links_one(lead, **kwargs):
        return lead

    monkeypatch.setattr(orchestrator_module, "enrich_one", fake_enrich_one)
    monkeypatch.setattr(orchestrator_module, "discover_social_links_one", instant_discover_social_links_one)

    pool = _build_fake_pool(8)
    concurrency = PipelineConcurrency(enrichment_worker_count=3, social_worker_count=5)
    orchestrator = PipelineOrchestrator(concurrency=concurrency)
    request = SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=8)

    await orchestrator.run(request, browser_pool=pool)

    assert max_in_flight == 3


@pytest.mark.asyncio
async def test_social_worker_count_bounds_concurrent_social_discovery(monkeypatch) -> None:
    """PipelineConcurrency.social_worker_count must cap how many
    discover_social_links_one calls the streaming pipeline runs
    concurrently -- verified the same way as the enrichment test above,
    with enrichment kept instant here so a backlog of leads actually
    reaches the social queue for social's own worker count to bound,
    rather than enrichment's (slower) production rate being the limiter.
    """
    import app.pipeline.orchestrator as orchestrator_module

    in_flight = 0
    max_in_flight = 0

    async def instant_enrich_one(pool, lead, **kwargs):
        return lead

    async def fake_discover_social_links_one(lead, **kwargs):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return lead

    monkeypatch.setattr(orchestrator_module, "enrich_one", instant_enrich_one)
    monkeypatch.setattr(orchestrator_module, "discover_social_links_one", fake_discover_social_links_one)

    pool = _build_fake_pool(20)
    concurrency = PipelineConcurrency(enrichment_worker_count=4, social_worker_count=5)
    orchestrator = PipelineOrchestrator(concurrency=concurrency)
    request = SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=20)

    await orchestrator.run(request, browser_pool=pool)

    assert max_in_flight == 5


@pytest.mark.asyncio
async def test_a_failing_lead_does_not_crash_the_pipeline(monkeypatch) -> None:
    """Per-lead failure isolation in the streaming pipeline: every
    enrichment attempt raises, but all leads still flow through to the
    final result (website stays None for each) instead of the whole run
    aborting -- the same resilience guarantee the old batch-mode
    enrich_batch provided, now enforced per-item by the worker loop."""
    import app.pipeline.orchestrator as orchestrator_module

    async def broken_enrich_one(pool, lead, **kwargs):
        raise RuntimeError("enrichment exploded")

    monkeypatch.setattr(orchestrator_module, "enrich_one", broken_enrich_one)

    pool = _build_fake_pool(3)
    fetcher, extractor, fallback = _build_fake_social(3)
    orchestrator = PipelineOrchestrator()
    request = SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=3)

    result = await orchestrator.run(
        request, browser_pool=pool, social_fetcher=fetcher, social_extractor=extractor, social_fallback=fallback
    )

    # Discovery's leads survive even though every enrichment attempt blew up.
    assert len(result.leads) == 3
    assert all(lead.website is None for lead in result.leads)


@pytest.mark.asyncio
async def test_request_cancellation_stops_before_the_next_stage() -> None:
    pool = _build_fake_pool(3)
    orchestrator = PipelineOrchestrator()
    request = SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=3)

    # Cancel immediately, before run() even starts stage 1.
    orchestrator.request_cancellation()
    result = await orchestrator.run(request, browser_pool=pool)

    # No stages ran at all, so leads stay empty and no stage times recorded.
    assert result.leads == []
    assert result.metrics.stage_times == {}


@pytest.mark.asyncio
async def test_owned_browser_resources_are_started_and_stopped() -> None:
    fake_manager = MagicMock()
    fake_manager.start = AsyncMock()
    fake_manager.stop = AsyncMock()
    fake_manager.browser = MagicMock()

    pool = _build_fake_pool(2)
    pool.start = AsyncMock()
    pool.stop = AsyncMock()
    fetcher, extractor, fallback = _build_fake_social(2)

    import app.pipeline.orchestrator as orchestrator_module

    monkeypatch_pool_cls = MagicMock(return_value=pool)
    original_pool_cls = orchestrator_module.BrowserContextPool
    orchestrator_module.BrowserContextPool = monkeypatch_pool_cls
    try:
        orchestrator = PipelineOrchestrator()
        request = SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=2)
        await orchestrator.run(
            request,
            browser_manager=fake_manager,
            social_fetcher=fetcher,
            social_extractor=extractor,
            social_fallback=fallback,
        )
    finally:
        orchestrator_module.BrowserContextPool = original_pool_cls

    fake_manager.start.assert_awaited_once()
    fake_manager.stop.assert_awaited_once()
    pool.start.assert_awaited_once()
    pool.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_injected_browser_pool_lifecycle_is_not_managed_by_orchestrator() -> None:
    """When the caller supplies its own pool (as benchmarks/tests do),
    the orchestrator must not call start()/stop() on it — that pool's
    lifecycle belongs to whoever created it."""
    pool = _build_fake_pool(2)
    fetcher, extractor, fallback = _build_fake_social(2)
    # Deliberately no start/stop attributes at all on FakeOrchestratorPool —
    # if the orchestrator tried to call them, this test would raise
    # AttributeError.
    orchestrator = PipelineOrchestrator()
    request = SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=2)

    result = await orchestrator.run(
        request, browser_pool=pool, social_fetcher=fetcher, social_extractor=extractor, social_fallback=fallback
    )
    assert len(result.leads) == 2
