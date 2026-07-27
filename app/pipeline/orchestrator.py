"""Orchestrates the full lead-generation pipeline by composing the
existing, independently-built stages from Phases 3-6:

    Maps Discovery -> Website Enrichment -> Social Discovery -> URL Selection

This module contains ONLY orchestration: it calls the existing public
APIs of each phase and passes data between them. No discovery,
enrichment, social-discovery, networking, or selection logic is
implemented or modified here.

Phase A: Website Enrichment, Social Discovery, and URL Selection now run
as a streaming producer/consumer pipeline -- two bounded queues connect
three pools of workers -- instead of three sequential whole-batch passes.
A business moves to the next stage the moment it finishes the current
one, instead of every business waiting for the whole batch to clear a
stage first. Maps Discovery is unchanged: it is one continuous Playwright
search/scroll session on a single page and still returns its full result
at once, exactly as before -- splitting Discovery's own internals was out
of scope for this change.

`WebsiteEnrichmentStage`, `SocialDiscoveryStage`, and `UrlSelectionStage`
below are kept exactly as they were (whole-batch, callable independently)
so they remain usable and testable standalone. `PipelineOrchestrator.run()`
no longer drives them in a barrier loop -- it streams leads through
`enrich_one` / `discover_social_links_one` / `SelectionEngine` directly
via `_stream_enrichment_social_selection`, the same per-lead functions
those batch stages call internally, just scheduled differently.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.discovery.google_maps.browser_manager import BrowserManager
from app.discovery.google_maps.browser_pool import BrowserContextPool
from app.discovery.google_maps.pipeline import run_discovery
from app.enrichment.google_maps.batch import enrich_one
from app.enrichment.google_maps.workers import enrich_batch
from app.enrichment.social.batch import discover_social_links_one
from app.enrichment.social.browser_html_fetcher import BrowserWebsiteHTMLFetcher
from app.enrichment.social.confidence import Confidence
from app.enrichment.social.workers import discover_social_batch
from app.models.domain import BusinessLead
from app.network.session_manager import SessionManager
from app.pipeline.base import PipelineStage
from app.pipeline.metrics import PipelineMetrics, PipelineMetricsSnapshot
from app.pipeline.progress import PipelineProgressSnapshot, PipelineProgressTracker
from app.schemas.search import SearchRequest
from app.selection.candidate import Candidate, make_candidate
from app.selection.engine import SelectionEngine

logger = get_logger(__name__)

# Put onto a stage queue to mean "no more leads will ever arrive here" --
# one is fed per worker consuming that queue, so every worker exits
# cleanly once the real leads ahead of it are drained (queues are FIFO,
# so no worker can see this before all real leads have been handed to
# some worker).
_QUEUE_DONE = object()


@dataclass
class PipelineConcurrency:
    """Configurable worker counts per stage. None = use that stage's own
    existing Settings default — this only threads through parameters each
    stage's per-lead function already accepts; it adds no new concurrency
    mechanism of its own."""

    discovery_pool_size: Optional[int] = None
    enrichment_worker_count: Optional[int] = None
    social_worker_count: Optional[int] = None


@dataclass
class OrchestratorContext:
    request: SearchRequest
    browser_pool: Any  # BrowserContextPool, or any object exposing an equivalent .acquire()
    concurrency: PipelineConcurrency
    social_fetcher: Optional[Any] = None
    social_extractor: Optional[Any] = None
    social_fallback: Optional[Any] = None
    leads: List[BusinessLead] = field(default_factory=list)
    progress: Optional[PipelineProgressTracker] = None
    metrics: Optional[PipelineMetrics] = None


def _parse_confidence(value: Optional[str]) -> Confidence:
    if value is None:
        return Confidence.LOW
    try:
        return Confidence(value)
    except ValueError:
        return Confidence.LOW


def _candidates_from_lead(lead: BusinessLead) -> List[Candidate]:
    """Adapts a lead's already-discovered social URLs (Phase 5's output)
    into Phase 6 Candidate objects, so the existing SelectionEngine can
    validate/normalize/clean them up as a final pass. This adapter lives
    here, not inside Phase 5 or Phase 6, so neither is modified."""
    candidates: List[Candidate] = []
    if lead.social.instagram_url:
        candidates.append(
            make_candidate(
                platform="instagram",
                url=lead.social.instagram_url,
                source="social_discovery",
                confidence=_parse_confidence(lead.social.instagram_confidence),
            )
        )
    if lead.social.facebook_url:
        candidates.append(
            make_candidate(
                platform="facebook",
                url=lead.social.facebook_url,
                source="social_discovery",
                confidence=_parse_confidence(lead.social.facebook_confidence),
            )
        )
    return candidates


class MapsDiscoveryStage(PipelineStage[OrchestratorContext, OrchestratorContext]):
    name = "maps_discovery"

    async def process(self, context: OrchestratorContext) -> OrchestratorContext:
        if context.progress:
            context.progress.start_stage(self.name)
        start = time.perf_counter()

        async with context.browser_pool.acquire() as page:
            result = await run_discovery(
                page,
                keyword=context.request.keyword,
                location=context.request.location,
                limit=context.request.limit,
            )
        context.leads = result.leads

        if context.metrics:
            context.metrics.record_stage_time(self.name, time.perf_counter() - start)
        if context.progress:
            context.progress.finish_stage(self.name, completed=len(context.leads), failed=0)
        return context


class WebsiteEnrichmentStage(PipelineStage[OrchestratorContext, OrchestratorContext]):
    """Whole-batch version of this stage, kept as-is so it stays usable
    and testable standalone (see tests/pipeline/test_stages.py). A live
    `PipelineOrchestrator.run()` no longer calls this -- it streams leads
    through `enrich_one` directly instead; see
    `PipelineOrchestrator._stream_enrichment_social_selection`."""

    name = "website_enrichment"

    async def process(self, context: OrchestratorContext) -> OrchestratorContext:
        if context.progress:
            context.progress.start_stage(self.name)
        start = time.perf_counter()

        needed = [lead for lead in context.leads if lead.website is None and lead.social.google_maps_url]
        await enrich_batch(context.browser_pool, context.leads, worker_count=context.concurrency.enrichment_worker_count)
        completed = sum(1 for lead in needed if lead.website is not None)
        failed = len(needed) - completed

        if context.metrics:
            context.metrics.record_stage_time(self.name, time.perf_counter() - start)
        if context.progress:
            context.progress.finish_stage(self.name, completed=completed, failed=failed)
        return context


class SocialDiscoveryStage(PipelineStage[OrchestratorContext, OrchestratorContext]):
    """Whole-batch version of this stage, kept as-is so it stays usable
    and testable standalone (see tests/pipeline/test_stages.py). A live
    `PipelineOrchestrator.run()` no longer calls this -- it streams leads
    through `discover_social_links_one` directly instead; see
    `PipelineOrchestrator._stream_enrichment_social_selection`."""

    name = "social_discovery"

    async def process(self, context: OrchestratorContext) -> OrchestratorContext:
        if context.progress:
            context.progress.start_stage(self.name)
        start = time.perf_counter()

        needed = [
            lead for lead in context.leads if lead.social.instagram_url is None or lead.social.facebook_url is None
        ]
        await discover_social_batch(
            context.leads,
            worker_count=context.concurrency.social_worker_count,
            fetcher=context.social_fetcher,
            extractor=context.social_extractor,
            fallback=context.social_fallback,
        )
        completed = sum(1 for lead in needed if lead.social.instagram_url or lead.social.facebook_url)
        failed = len(needed) - completed

        if context.metrics:
            context.metrics.record_stage_time(self.name, time.perf_counter() - start)
        if context.progress:
            context.progress.finish_stage(self.name, completed=completed, failed=failed)
        return context


class UrlSelectionStage(PipelineStage[OrchestratorContext, OrchestratorContext]):
    """Whole-batch version of this stage, kept as-is so it stays usable
    and testable standalone (see tests/pipeline/test_stages.py). A live
    `PipelineOrchestrator.run()` no longer calls this -- it applies
    `SelectionEngine` inline right after social discovery per-lead; see
    `PipelineOrchestrator._stream_enrichment_social_selection`."""

    name = "url_selection"

    async def process(self, context: OrchestratorContext) -> OrchestratorContext:
        if context.progress:
            context.progress.start_stage(self.name)
        start = time.perf_counter()

        engine = SelectionEngine()
        before = sum(1 for lead in context.leads if lead.social.instagram_url or lead.social.facebook_url)

        for lead in context.leads:
            candidates = _candidates_from_lead(lead)
            if not candidates:
                continue
            result = engine.select(candidates)
            lead.social.instagram_url = result.instagram_url
            if not result.instagram_url:
                lead.social.instagram_confidence = None
            lead.social.facebook_url = result.facebook_url
            if not result.facebook_url:
                lead.social.facebook_confidence = None

        after = sum(1 for lead in context.leads if lead.social.instagram_url or lead.social.facebook_url)
        completed = after
        failed = max(0, before - after)

        if context.metrics:
            context.metrics.record_stage_time(self.name, time.perf_counter() - start)
        if context.progress:
            context.progress.finish_stage(self.name, completed=completed, failed=failed)
        return context


@dataclass
class PipelineResult:
    leads: List[BusinessLead]
    progress: PipelineProgressSnapshot
    metrics: PipelineMetricsSnapshot


class PipelineOrchestrator:
    """Runs Maps Discovery, then streams leads through Website Enrichment,
    Social Discovery, and URL Selection concurrently, for one
    SearchRequest. Owns the browser resources it creates (graceful
    cleanup guaranteed via try/finally, satisfying cancellation
    requirements) unless the caller injects its own already-managed
    browser_pool (e.g. for tests/benchmarks), in which case lifecycle is
    the caller's responsibility.
    """

    def __init__(self, *, concurrency: Optional[PipelineConcurrency] = None) -> None:
        self._concurrency = concurrency or PipelineConcurrency()
        self._cancel_event = asyncio.Event()

    def request_cancellation(self) -> None:
        """Signals the orchestrator to stop starting new work, letting
        whatever is currently in flight finish naturally (a graceful
        stop, not an abrupt one). For immediate/hard cancellation, cancel
        the asyncio Task running `run()` instead -- cleanup happens
        either way via the try/finally in `run()`.

        Can be called either before `run()` starts (the pipeline then
        does nothing at all) or concurrently while it's in progress. A
        PipelineOrchestrator is cheap to construct — build a new instance
        per run rather than reusing one across runs, so a prior
        cancellation can never leak into a later run.
        """
        self._cancel_event.set()

    async def _stream_enrichment_social_selection(self, context: OrchestratorContext) -> None:
        """Streams `context.leads` through Website Enrichment, Social
        Discovery, and URL Selection as a producer/consumer pipeline: two
        bounded queues connect three pools of workers, so a lead moves to
        the next stage the moment it finishes the current one instead of
        the whole batch waiting to clear each stage first. Calls the same
        per-lead functions the batch stage classes above call internally
        (`enrich_one`, `discover_social_links_one`, `SelectionEngine`) --
        only the scheduling around them changes.

        Selection runs inline immediately after social discovery for the
        same lead (both are cheap/local relative to enrichment's browser
        navigation and social's network calls), so no third queue is
        needed.
        """
        settings = get_settings()
        enrichment_workers = context.concurrency.enrichment_worker_count or settings.ENRICHMENT_WORKER_COUNT
        social_workers = context.concurrency.social_worker_count or settings.MAX_SEARCH_WORKERS

        to_enrich: "asyncio.Queue[Any]" = asyncio.Queue(maxsize=max(2 * enrichment_workers, 1))
        to_social: "asyncio.Queue[Any]" = asyncio.Queue(maxsize=max(2 * social_workers, 1))

        enrichment_needed_ids = {
            id(lead) for lead in context.leads if not lead.website and lead.social.google_maps_url
        }

        counts = {
            "enrichment_completed": 0,
            "enrichment_failed": 0,
            "social_completed": 0,
            "social_failed": 0,
            "selection_before": 0,
            "selection_after": 0,
            "selection_time": 0.0,
        }

        async def feed_enrichment() -> None:
            for lead in context.leads:
                await to_enrich.put(lead)
            for _ in range(enrichment_workers):
                await to_enrich.put(_QUEUE_DONE)

        async def enrichment_worker() -> None:
            while True:
                lead = await to_enrich.get()
                if lead is _QUEUE_DONE:
                    return
                try:
                    if id(lead) in enrichment_needed_ids and not self._cancel_event.is_set():
                        try:
                            await enrich_one(context.browser_pool, lead)
                        except Exception:
                            logger.warning(
                                "Failed to enrich '%s' after retries; leaving website as None",
                                lead.business_name,
                                exc_info=True,
                            )
                        if lead.website is not None:
                            counts["enrichment_completed"] += 1
                        else:
                            counts["enrichment_failed"] += 1
                except Exception:
                    logger.exception("Unexpected error streaming '%s' through enrichment", lead.business_name)
                # Always forward downstream, even on failure/cancellation,
                # so a lead is never dropped from the final result.
                await to_social.put(lead)

        engine = SelectionEngine()

        async def social_worker() -> None:
            while True:
                lead = await to_social.get()
                if lead is _QUEUE_DONE:
                    return
                try:
                    needs_social = lead.social.instagram_url is None or lead.social.facebook_url is None
                    if needs_social:
                        if not self._cancel_event.is_set():
                            try:
                                await discover_social_links_one(
                                    lead,
                                    fetcher=context.social_fetcher,
                                    extractor=context.social_extractor,
                                    fallback=context.social_fallback,
                                )
                            except Exception:
                                logger.warning(
                                    "Failed to discover social links for '%s'", lead.business_name, exc_info=True
                                )
                        if lead.social.instagram_url or lead.social.facebook_url:
                            counts["social_completed"] += 1
                        else:
                            counts["social_failed"] += 1

                    had_url = bool(lead.social.instagram_url or lead.social.facebook_url)
                    if had_url:
                        counts["selection_before"] += 1
                    candidates = _candidates_from_lead(lead)
                    if candidates:
                        select_start = time.perf_counter()
                        result = engine.select(candidates)
                        counts["selection_time"] += time.perf_counter() - select_start
                        lead.social.instagram_url = result.instagram_url
                        if not result.instagram_url:
                            lead.social.instagram_confidence = None
                        lead.social.facebook_url = result.facebook_url
                        if not result.facebook_url:
                            lead.social.facebook_confidence = None
                    if lead.social.instagram_url or lead.social.facebook_url:
                        counts["selection_after"] += 1
                except Exception:
                    logger.exception("Unexpected error streaming '%s' through social/selection", lead.business_name)

        if context.progress:
            context.progress.start_stage(WebsiteEnrichmentStage.name)
        enrichment_start = time.perf_counter()
        enrichment_tasks = [asyncio.create_task(enrichment_worker()) for _ in range(enrichment_workers)]
        feeder_task = asyncio.create_task(feed_enrichment())

        if context.progress:
            context.progress.start_stage(SocialDiscoveryStage.name)
            context.progress.start_stage(UrlSelectionStage.name)
        social_start = time.perf_counter()
        social_tasks = [asyncio.create_task(social_worker()) for _ in range(social_workers)]

        await asyncio.gather(feeder_task, *enrichment_tasks)
        enrichment_elapsed = time.perf_counter() - enrichment_start

        for _ in range(social_workers):
            await to_social.put(_QUEUE_DONE)
        await asyncio.gather(*social_tasks)
        social_elapsed = time.perf_counter() - social_start

        if context.metrics:
            context.metrics.record_stage_time(WebsiteEnrichmentStage.name, enrichment_elapsed)
            context.metrics.record_stage_time(SocialDiscoveryStage.name, social_elapsed)
            context.metrics.record_stage_time(UrlSelectionStage.name, counts["selection_time"])
        if context.progress:
            context.progress.finish_stage(
                WebsiteEnrichmentStage.name,
                completed=counts["enrichment_completed"],
                failed=counts["enrichment_failed"],
            )
            context.progress.finish_stage(
                SocialDiscoveryStage.name,
                completed=counts["social_completed"],
                failed=counts["social_failed"],
            )
            context.progress.finish_stage(
                UrlSelectionStage.name,
                completed=counts["selection_after"],
                failed=max(0, counts["selection_before"] - counts["selection_after"]),
            )

    async def run(
        self,
        request: SearchRequest,
        *,
        browser_manager: Optional[BrowserManager] = None,
        browser_pool: Optional[Any] = None,
        social_fetcher: Optional[Any] = None,
        social_extractor: Optional[Any] = None,
        social_fallback: Optional[Any] = None,
    ) -> PipelineResult:
        owns_browser_resources = browser_pool is None
        if owns_browser_resources:
            browser_manager = browser_manager or BrowserManager()
            browser_pool = BrowserContextPool(browser_manager, pool_size=self._concurrency.discovery_pool_size)

        if social_fetcher is None:
            # Plain HTTP GETs a business's homepage, but several real sites
            # verified live return a near-empty stub to a non-browser
            # client (their real content is only served/rendered for a
            # browser-like request) -- so the default path renders through
            # the same pooled browser Maps discovery/enrichment already
            # use, instead of missing footer social links that are
            # genuinely there.
            social_fetcher = BrowserWebsiteHTMLFetcher(browser_pool)

        progress = PipelineProgressTracker()
        metrics = PipelineMetrics()
        context = OrchestratorContext(
            request=request,
            browser_pool=browser_pool,
            concurrency=self._concurrency,
            social_fetcher=social_fetcher,
            social_extractor=social_extractor,
            social_fallback=social_fallback,
            progress=progress,
            metrics=metrics,
        )

        try:
            if owns_browser_resources:
                await browser_manager.start()
                await browser_pool.start()
            await SessionManager.get_instance().startup()

            if self._cancel_event.is_set():
                logger.info("Pipeline cancellation requested; stopping before stage '%s'", MapsDiscoveryStage.name)
            else:
                try:
                    context = await MapsDiscoveryStage().process(context)
                except Exception:
                    logger.exception(
                        "Stage '%s' failed; continuing with %d leads carried over from before this stage",
                        MapsDiscoveryStage.name,
                        len(context.leads),
                    )
                    if context.progress:
                        context.progress.finish_stage(MapsDiscoveryStage.name, completed=0, failed=len(context.leads))

                if self._cancel_event.is_set():
                    logger.info(
                        "Pipeline cancellation requested; stopping before stage '%s'", WebsiteEnrichmentStage.name
                    )
                else:
                    try:
                        await self._stream_enrichment_social_selection(context)
                    except Exception:
                        logger.exception(
                            "Streaming enrichment/social/selection failed; returning %d leads as-is",
                            len(context.leads),
                        )
        finally:
            if owns_browser_resources:
                try:
                    await browser_pool.stop()
                except Exception:
                    logger.exception("Error while stopping the browser pool")
                try:
                    await browser_manager.stop()
                except Exception:
                    logger.exception("Error while stopping the browser manager")

        total = len(context.leads)
        successful = sum(
            1 for lead in context.leads if lead.website and (lead.social.instagram_url or lead.social.facebook_url)
        )

        return PipelineResult(
            leads=context.leads,
            progress=progress.snapshot(),
            metrics=metrics.snapshot(total_businesses=total, successful_businesses=successful),
        )
