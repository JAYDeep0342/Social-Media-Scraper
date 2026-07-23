"""Single-lead enrichment: opens a business's detail panel (only if its
website is missing), extracts the website if listed, validates/normalizes
it, and checks/updates the enrichment cache. Composed by workers.py to
process a batch across parallel workers.
"""

from typing import Optional

from app.discovery.google_maps.browser_pool import BrowserContextPool
from app.enrichment.google_maps.cache import EnrichmentCache
from app.enrichment.google_maps.detail_navigator import DetailPanelNavigator
from app.enrichment.google_maps.website_extractor import WebsiteExtractor
from app.enrichment.google_maps.website_validator import validate_and_normalize_website
from app.models.domain import BusinessLead
from app.network.retry_strategy import RetryPolicy


async def enrich_one(
    pool: BrowserContextPool,
    lead: BusinessLead,
    *,
    cache: Optional[EnrichmentCache] = None,
    retry_policy: Optional[RetryPolicy] = None,
) -> BusinessLead:
    """Enriches `lead.website` in place if it's missing and a Google Maps
    URL is available. Leaves leads that already have a website, or have no
    Maps URL to look up, untouched. Returns the same lead instance."""
    if lead.website or not lead.social.google_maps_url:
        return lead

    maps_url = lead.social.google_maps_url

    if cache is not None:
        cached = await cache.get(maps_url)
        if cached is not None:
            lead.website = cached.website
            return lead

    async with pool.acquire() as page:
        navigator = DetailPanelNavigator(page, retry_policy=retry_policy)
        await navigator.open(maps_url)
        extractor = WebsiteExtractor(page)
        raw_website = await extractor.extract()

    website = validate_and_normalize_website(raw_website)
    lead.website = website

    if cache is not None:
        await cache.set(maps_url, website)

    return lead
