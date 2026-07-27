"""Single-business social discovery: fetch the business's homepage HTML,
extract Instagram/Facebook links, and fall back to a DuckDuckGo search only
if the website has none. Composed by workers.py for parallel batch
processing.

When both Instagram and Facebook need the search-engine fallback, the two
lookups run concurrently (`asyncio.gather`) rather than one after the
other -- they're independent queries against the same DuckDuckGo endpoint,
so there's no reason for one business's Facebook lookup to wait on its own
Instagram lookup finishing first.
"""

import asyncio
from typing import Optional

from app.core.logging import get_logger
from app.enrichment.social.confidence import Confidence, is_canonical_social_url
from app.enrichment.social.dedup import deduplicate_candidates
from app.enrichment.social.html_fetcher import WebsiteHTMLFetcher
from app.enrichment.social.link_extractor import SocialLinkExtractor, classify_platform
from app.enrichment.social.metrics import SocialDiscoveryMetrics
from app.enrichment.social.search_fallback import SocialSearchFallback
from app.enrichment.social.url_normalizer import normalize_social_url
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

    # Google Maps' "website" field is sometimes actually a link straight
    # to the business's Instagram/Facebook -- small businesses often list
    # only that, no real site. Recognize it as that platform's URL
    # directly instead of fetching it as if it were a generic homepage:
    # Instagram/Facebook block or require JS for a plain HTTP fetch, so
    # that fetch would just fail and silently throw away a signal we
    # already have straight from the business's own Maps listing.
    website_is_social_platform = False
    website_found_any = False
    if lead.website:
        website_platform = classify_platform(lead.website)
        if website_platform is not None:
            website_is_social_platform = True
        if website_platform == "instagram" and needs_instagram:
            try:
                lead.social.instagram_url = normalize_social_url(lead.website)
                lead.social.instagram_confidence = Confidence.HIGH.value
                needs_instagram = False
                website_found_any = True
            except Exception:
                logger.debug("Failed to normalize website-as-Instagram URL: %s", lead.website, exc_info=True)
        elif website_platform == "facebook" and needs_facebook:
            try:
                lead.social.facebook_url = normalize_social_url(lead.website)
                lead.social.facebook_confidence = Confidence.HIGH.value
                needs_facebook = False
                website_found_any = True
            except Exception:
                logger.debug("Failed to normalize website-as-Facebook URL: %s", lead.website, exc_info=True)

    website_candidates = []
    if (needs_instagram or needs_facebook) and lead.website and not website_is_social_platform:
        html = await fetcher.fetch(lead.website)
        if metrics is not None:
            await metrics.record_html_fetch(html is not None)
        if html:
            website_candidates = deduplicate_candidates(extractor.extract(html))

    if needs_instagram:
        match = next((c for c in website_candidates if c.platform == "instagram"), None)
        if match:
            lead.social.instagram_url = match.url
            lead.social.instagram_confidence = (
                Confidence.HIGH if is_canonical_social_url(match.url, "instagram") else Confidence.MEDIUM
            ).value
            website_found_any = True
            needs_instagram = False

    if needs_facebook:
        match = next((c for c in website_candidates if c.platform == "facebook"), None)
        if match:
            lead.social.facebook_url = match.url
            lead.social.facebook_confidence = (
                Confidence.HIGH if is_canonical_social_url(match.url, "facebook") else Confidence.MEDIUM
            ).value
            website_found_any = True
            needs_facebook = False

    if website_found_any and metrics is not None:
        await metrics.record_website_success()

    used_fallback = False
    instagram_fallback_result = None
    facebook_fallback_result = None

    if needs_instagram and needs_facebook:
        instagram_fallback_result, facebook_fallback_result = await asyncio.gather(
            fallback.find(lead.business_name, "instagram"),
            fallback.find(lead.business_name, "facebook"),
        )
    elif needs_instagram:
        instagram_fallback_result = await fallback.find(lead.business_name, "instagram")
    elif needs_facebook:
        facebook_fallback_result = await fallback.find(lead.business_name, "facebook")

    if needs_instagram and instagram_fallback_result is not None:
        url, is_canonical = instagram_fallback_result
        if url:
            lead.social.instagram_url = url
            lead.social.instagram_confidence = (Confidence.MEDIUM if is_canonical else Confidence.LOW).value
            used_fallback = True

    if needs_facebook and facebook_fallback_result is not None:
        url, is_canonical = facebook_fallback_result
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
