"""Assembles the Google Maps discovery pipeline: Search -> Scroll -> Collect
Cards -> Deduplicate -> Return, built on the generic app.pipeline framework
(PipelineStage/Pipeline from Phase 1.1).

A single mutable DiscoveryContext is threaded through the stages via
Pipeline.run_one(); each stage reads/updates it and passes it along.
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional

from playwright.async_api import Page

from app.discovery.google_maps.card_extractor import CardExtractor
from app.discovery.google_maps.dedup import deduplicate_leads
from app.discovery.google_maps.maps_navigator import MapsNavigator
from app.discovery.google_maps.metrics import DiscoveryMetrics
from app.discovery.google_maps.progress_tracker import ProgressTracker
from app.discovery.google_maps.scroll_engine import ScrollEngine, ScrollResult
from app.models.domain import BusinessLead
from app.pipeline.base import Pipeline, PipelineStage


@dataclass
class DiscoveryContext:
    page: Page
    keyword: str
    location: str
    limit: int
    leads: List[BusinessLead] = field(default_factory=list)
    scroll_result: Optional[ScrollResult] = None
    duplicate_count: int = 0
    progress: Optional[ProgressTracker] = None
    # Optional per-run scroll tuning (None = use settings defaults). Lets
    # callers trade thoroughness for speed without touching global config.
    scroll_base_pause_seconds: Optional[float] = None
    scroll_max_attempts_without_progress: Optional[int] = None
    scroll_max_total_attempts: Optional[int] = None


class SearchStage(PipelineStage[DiscoveryContext, DiscoveryContext]):
    name = "search"

    async def process(self, context: DiscoveryContext) -> DiscoveryContext:
        navigator = MapsNavigator(context.page)
        await navigator.search(context.keyword, context.location)
        context.progress = ProgressTracker(context.limit)
        return context


class ScrollStage(PipelineStage[DiscoveryContext, DiscoveryContext]):
    name = "scroll"

    async def process(self, context: DiscoveryContext) -> DiscoveryContext:
        engine = ScrollEngine(
            context.page,
            base_pause_seconds=context.scroll_base_pause_seconds,
            max_attempts_without_progress=context.scroll_max_attempts_without_progress,
            max_total_attempts=context.scroll_max_total_attempts,
        )
        context.scroll_result = await engine.scroll_until(context.limit)
        return context


class CollectCardsStage(PipelineStage[DiscoveryContext, DiscoveryContext]):
    name = "collect_cards"

    async def process(self, context: DiscoveryContext) -> DiscoveryContext:
        extractor = CardExtractor(context.page)
        leads = await extractor.extract_all(source_keyword=context.keyword, source_location=context.location)
        context.leads = leads[: context.limit] if len(leads) > context.limit else leads
        if context.progress is not None:
            context.progress.update(len(context.leads))
        return context


class DeduplicateStage(PipelineStage[DiscoveryContext, DiscoveryContext]):
    name = "deduplicate"

    async def process(self, context: DiscoveryContext) -> DiscoveryContext:
        unique, duplicate_count = deduplicate_leads(context.leads)
        context.leads = unique
        context.duplicate_count = duplicate_count
        return context


def build_discovery_pipeline() -> Pipeline:
    return Pipeline([SearchStage(), ScrollStage(), CollectCardsStage(), DeduplicateStage()], concurrency=1)


@dataclass
class DiscoveryResult:
    leads: List[BusinessLead]
    metrics: DiscoveryMetrics


async def run_discovery(
    page: Page,
    *,
    keyword: str,
    location: str,
    limit: int,
    scroll_base_pause_seconds: Optional[float] = None,
    scroll_max_attempts_without_progress: Optional[int] = None,
    scroll_max_total_attempts: Optional[int] = None,
) -> DiscoveryResult:
    context = DiscoveryContext(
        page=page,
        keyword=keyword,
        location=location,
        limit=limit,
        scroll_base_pause_seconds=scroll_base_pause_seconds,
        scroll_max_attempts_without_progress=scroll_max_attempts_without_progress,
        scroll_max_total_attempts=scroll_max_total_attempts,
    )
    pipeline = build_discovery_pipeline()

    start = time.perf_counter()
    result_context = await pipeline.run_one(context)
    elapsed = time.perf_counter() - start

    cards_collected = len(result_context.leads)
    metrics = DiscoveryMetrics(
        discovery_time_seconds=round(elapsed, 3),
        cards_collected=cards_collected,
        cards_per_second=round(cards_collected / elapsed, 2) if elapsed > 0 else 0.0,
        scroll_count=result_context.scroll_result.scroll_count if result_context.scroll_result else 0,
        duplicate_count=result_context.duplicate_count,
    )
    return DiscoveryResult(leads=result_context.leads, metrics=metrics)
