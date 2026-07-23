"""Runs batch enrichment across a configurable number of parallel workers,
each borrowing a page from the existing browser context pool (Phase 3) via
app.utils.async_helper.gather_with_concurrency (Phase 1).

Only leads missing a website are processed — everything else passes
through untouched. A single lead that fails to enrich (even after Phase 2
retries are exhausted) is logged and skipped rather than aborting the
whole batch, matching the resilience pattern used by the discovery card
extractor (Phase 3).
"""

from typing import List, Optional

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.discovery.google_maps.browser_pool import BrowserContextPool
from app.enrichment.google_maps.batch import enrich_one
from app.enrichment.google_maps.cache import EnrichmentCache
from app.enrichment.google_maps.metrics import EnrichmentMetrics
from app.models.domain import BusinessLead
from app.network.retry_strategy import RetryPolicy
from app.utils.async_helper import gather_with_concurrency

logger = get_logger(__name__)


async def enrich_batch(
    pool: BrowserContextPool,
    leads: List[BusinessLead],
    *,
    worker_count: Optional[int] = None,
    cache: Optional[EnrichmentCache] = None,
    metrics: Optional[EnrichmentMetrics] = None,
    retry_policy: Optional[RetryPolicy] = None,
) -> List[BusinessLead]:
    """Enriches `leads` in place and returns the same list. Only leads with
    a missing website (and a usable Maps URL) are sent through the worker
    pool; the rest are returned unchanged."""
    settings = get_settings()
    concurrency = worker_count or settings.ENRICHMENT_WORKER_COUNT

    needs_enrichment = [lead for lead in leads if not lead.website and lead.social.google_maps_url]

    async def _enrich_and_record(lead: BusinessLead) -> None:
        start = await metrics.start_one() if metrics is not None else None
        try:
            await enrich_one(pool, lead, cache=cache, retry_policy=retry_policy)
        except Exception:
            logger.warning(
                "Failed to enrich '%s' after retries; leaving website as None", lead.business_name, exc_info=True
            )
            if metrics is not None:
                await metrics.finish_one(start, success=False)
            return
        if metrics is not None:
            await metrics.finish_one(start, success=lead.website is not None)

    if needs_enrichment:
        await gather_with_concurrency(concurrency, *(_enrich_and_record(lead) for lead in needs_enrichment))

    return leads
