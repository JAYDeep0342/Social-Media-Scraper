"""Social discovery: finds a business's Instagram/Facebook URLs from its
own official website first, falling back to a DuckDuckGo site: search only
when the website has none. Instagram/Facebook pages themselves are never
opened, and no profile content (followers, usernames, posts) is ever
read — only the URL string of the profile itself.
"""

from app.enrichment.social.batch import discover_social_links_one
from app.enrichment.social.confidence import Confidence, classify_confidence
from app.enrichment.social.dedup import deduplicate_candidates
from app.enrichment.social.html_fetcher import WebsiteHTMLFetcher
from app.enrichment.social.link_extractor import LinkCandidate, SocialLinkExtractor
from app.enrichment.social.metrics import SocialDiscoveryMetrics, SocialDiscoveryMetricsSnapshot
from app.enrichment.social.search_fallback import SocialSearchFallback
from app.enrichment.social.url_normalizer import normalize_social_url
from app.enrichment.social.workers import discover_social_batch

__all__ = [
    "WebsiteHTMLFetcher",
    "SocialLinkExtractor",
    "LinkCandidate",
    "normalize_social_url",
    "Confidence",
    "classify_confidence",
    "SocialSearchFallback",
    "deduplicate_candidates",
    "SocialDiscoveryMetrics",
    "SocialDiscoveryMetricsSnapshot",
    "discover_social_links_one",
    "discover_social_batch",
]
