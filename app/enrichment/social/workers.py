"""Runs social discovery across a configurable number of parallel workers.
Each worker fetches HTML via the shared Phase 2 SessionManager, which
already provides connection pooling/reuse/rate-limiting/retries — there's
no separate resource pool to manage here since this phase is HTTP-only.

Only leads missing at least one social URL are processed. A single lead
that fails (even after Phase 2's retries inside SessionManager are
exhausted) is logged and skipped rather than aborting the whole batch,
matching the resilience pattern used throughout this project (Phase 3/4).
"""

from typing import List, Optional

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.enrichment.social.batch import discover_social_links_one
from app.enrichment.social.html_fetcher import WebsiteHTMLFetcher
from app.enrichment.social.link_extractor import SocialLinkExtractor
from app.enrichment.social.metrics import SocialDiscoveryMetrics
from app.enrichment.social.search_fallback import SocialSearchFallback
from app.models.domain import BusinessLead
from app.utils.async_helper import gather_with_concurrency

logger = get_logger(__name__)


async def discover_social_batch(
    leads: List[BusinessLead],
    *,
    worker_count: Optional[int] = None,
    fetcher: Optional[WebsiteHTMLFetcher] = None,
    extractor: Optional[SocialLinkExtractor] = None,
    fallback: Optional[SocialSearchFallback] = None,
    metrics: Optional[SocialDiscoveryMetrics] = None,
) -> List[BusinessLead]:
    """Enriches `leads` in place and returns the same list."""
    settings = get_settings()
    concurrency = worker_count or settings.MAX_SEARCH_WORKERS

    needs_processing = [
        lead for lead in leads if lead.social.instagram_url is None or lead.social.facebook_url is None
    ]

    async def _process(lead: BusinessLead) -> None:
        try:
            await discover_social_links_one(
                lead, fetcher=fetcher, extractor=extractor, fallback=fallback, metrics=metrics
            )
        except Exception:
            logger.warning("Failed to discover social links for '%s'", lead.business_name, exc_info=True)

    if needs_processing:
        await gather_with_concurrency(concurrency, *(_process(lead) for lead in needs_processing))

    return leads
