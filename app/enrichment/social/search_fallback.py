"""Search-engine fallback for social discovery: when a business's own
website has no social links, search DuckDuckGo for
`site:instagram.com "Business Name"` / `site:facebook.com "Business Name"`
and return the most likely official profile URL — never opening
Instagram/Facebook directly, only reading DuckDuckGo's own result list.

Verified live: raw results are noisy — they can include ad/tracking
entries and non-profile sub-pages (post links, hashtag pages, reels), plus
canonical-shaped but unrelated accounts (typosquats, regional variants).
Filtering here is two-pass: prefer a clean canonical profile URL that
plausibly relates to the business name (MEDIUM confidence upstream), and
only fall back to *any* platform-domain result as a last resort (LOW
confidence upstream). Business-name comparison is used only to rank/filter
candidate URLs — never extracted or stored as a standalone attribute.
"""

import re
from typing import List, Optional, Tuple

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.enrichment.social.confidence import canonical_slug
from app.enrichment.social.url_normalizer import normalize_social_url
from app.providers.duckduckgo import DuckDuckGoSearchProvider

logger = get_logger(__name__)

_PLATFORM_DOMAINS = {"instagram": "instagram.com", "facebook": "facebook.com"}


def _looks_related(business_name: str, slug: str) -> bool:
    """Lightweight sanity filter to discard obviously unrelated
    canonical-shaped results (e.g. typosquats or unrelated pages)."""
    words = re.findall(r"[a-z0-9]+", business_name.lower())
    if not words:
        return True
    first_word = words[0]
    normalized_slug = re.sub(r"[^a-z0-9]", "", slug.lower())
    return first_word in normalized_slug


class SocialSearchFallback:
    def __init__(self, provider: Optional[DuckDuckGoSearchProvider] = None) -> None:
        self._provider = provider or DuckDuckGoSearchProvider()

    async def find(self, business_name: str, platform: str) -> Tuple[Optional[str], bool]:
        """Returns (url, is_canonical). `is_canonical` distinguishes a
        clean profile-URL match (MEDIUM confidence, upstream) from a
        weaker fallback match (LOW confidence, upstream)."""
        settings = get_settings()
        domain = _PLATFORM_DOMAINS[platform]
        query = f'site:{domain} "{business_name}"'

        raw_urls = await self._provider.discover(query, "", settings.SOCIAL_SEARCH_RESULT_LIMIT)

        platform_urls: List[str] = []
        for raw_url in raw_urls:
            if domain not in raw_url:
                continue  # discards ad/tracking results whose real target isn't this platform
            try:
                platform_urls.append(normalize_social_url(raw_url))
            except Exception:
                logger.debug("Skipping unnormalizable search result URL: %s", raw_url, exc_info=True)

        # First pass: a clean, canonical, plausibly-related profile URL.
        for url in platform_urls:
            slug = canonical_slug(url, platform)
            if slug and _looks_related(business_name, slug):
                return url, True

        # Second pass: any platform URL at all, even non-canonical (weak signal).
        if platform_urls:
            return platform_urls[0], False

        return None, False
