"""Single-business social discovery: fetch the business's homepage HTML,
extract Instagram/Facebook links, and fall back to a DuckDuckGo search only
if the website has none. Composed by workers.py for parallel batch
processing.
"""

from typing import Optional

from app.core.logging import get_logger
from app.enrichment.social.confidence import Confidence
from app.enrichment.social.dedup import deduplicate_candidates
from app.enrichment.social.html_fetcher import WebsiteHTMLFetcher
from app.enrichment.social.link_extractor import SocialLinkExtractor
from app.enrichment.social.metrics import SocialDiscoveryMetrics
from app.enrichment.social.search_fallback import SocialSearchFallback
from app.models.domain import BusinessLead

logger = get_logger(__name__)


async def discover_social_links_one(
    lead: BusinessLead,
    *,
    fetcher: Optional[WebsiteHTMLFetcher] = None,
    extractor: Optional[SocialLinkExtractor] = None,
    fallback: Optional[SocialSearchFallback] = None,
    metrics: Optional[SocialDiscoveryMetrics] = None,
) -> BusinessLead:
    """Populates lead.social.instagram_url/facebook_url (and their
    confidence tiers) in place, only for whichever is currently missing.
    Returns the same lead instance."""
    fetcher = fetcher or WebsiteHTMLFetcher()
    extractor = extractor or SocialLinkExtractor()
    fallback = fallback or SocialSearchFallback()

    start = await metrics.start_one() if metrics is not None else None

    needs_instagram = lead.social.instagram_url is None
    needs_facebook = lead.social.facebook_url is None

    website_candidates = []
    if (needs_instagram or needs_facebook) and lead.website:
        html = await fetcher.fetch(lead.website)
        if metrics is not None:
            await metrics.record_html_fetch(html is not None)
        if html:
            website_candidates = deduplicate_candidates(extractor.extract(html))

    website_found_any = False

    if needs_instagram:
        match = next((c for c in website_candidates if c.platform == "instagram"), None)
        if match:
            lead.social.instagram_url = match.url
            lead.social.instagram_confidence = Confidence.HIGH.value
            website_found_any = True
            needs_instagram = False

    if needs_facebook:
        match = next((c for c in website_candidates if c.platform == "facebook"), None)
        if match:
            lead.social.facebook_url = match.url
            lead.social.facebook_confidence = Confidence.HIGH.value
            website_found_any = True
            needs_facebook = False

    if website_found_any and metrics is not None:
        await metrics.record_website_success()

    used_fallback = False

    if needs_instagram:
        url, is_canonical = await fallback.find(lead.business_name, "instagram")
        if url:
            lead.social.instagram_url = url
            lead.social.instagram_confidence = (Confidence.MEDIUM if is_canonical else Confidence.LOW).value
            used_fallback = True

    if needs_facebook:
        url, is_canonical = await fallback.find(lead.business_name, "facebook")
        if url:
            lead.social.facebook_url = url
            lead.social.facebook_confidence = (Confidence.MEDIUM if is_canonical else Confidence.LOW).value
            used_fallback = True

    if used_fallback and metrics is not None:
        await metrics.record_search_fallback_used()

    if metrics is not None:
        await metrics.finish_one(
            start,
            instagram_found=lead.social.instagram_url is not None,
            facebook_found=lead.social.facebook_url is not None,
        )

    return lead
