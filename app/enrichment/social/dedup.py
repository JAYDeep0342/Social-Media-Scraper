"""Deduplicates normalized social link candidates extracted from a single
website, so multiple raw hrefs pointing at the same profile (e.g. one in
the header, one in the footer, with different tracking params) collapse
to a single entry.
"""

from typing import List, Set

from app.enrichment.social.link_extractor import LinkCandidate
from app.enrichment.social.url_normalizer import normalize_social_url


def deduplicate_candidates(candidates: List[LinkCandidate]) -> List[LinkCandidate]:
    """Keeps the first occurrence of each distinct normalized URL,
    preserving the source-priority ordering already established by
    SocialLinkExtractor.extract (footer/header before generic anchor)."""
    seen: Set[str] = set()
    unique: List[LinkCandidate] = []

    for candidate in candidates:
        try:
            normalized = normalize_social_url(candidate.url)
        except Exception:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(LinkCandidate(url=normalized, platform=candidate.platform, source=candidate.source))

    return unique
