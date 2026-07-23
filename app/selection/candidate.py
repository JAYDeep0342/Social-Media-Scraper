"""Represents a single discovered social URL as a candidate, prior to
ranking/deduplication/selection. Pure data — built entirely from URLs
already collected by earlier phases; this module never fetches anything.
"""

from dataclasses import dataclass
from typing import Optional

from app.enrichment.social.confidence import Confidence
from app.enrichment.social.url_normalizer import normalize_social_url
from app.utils.url_helper import is_valid_url


@dataclass(frozen=True, slots=True)
class Candidate:
    platform: str  # "instagram" | "facebook"
    url: str  # the raw URL as originally discovered
    source: str  # e.g. "footer", "json_ld", "search_fallback" (see app.selection.ranking._SOURCE_WEIGHTS)
    confidence: Confidence
    normalized_url: Optional[str] = None  # None if `url` is unusable (treated as rejected)


def make_candidate(*, platform: str, url: str, source: str, confidence: Confidence) -> Candidate:
    """Builds a Candidate, computing `normalized_url` via the existing
    Phase 5 normalizer (mobile-domain canonicalization, tracking-param
    stripping, trailing-slash removal). Never raises — a URL that can't be
    normalized, or normalizes to something that still isn't a well-formed
    URL (the normalizer is lenient by design; `is_valid_url` is not),
    yields `normalized_url=None` so the engine rejects it.
    """
    try:
        normalized: Optional[str] = normalize_social_url(url)
    except Exception:
        normalized = None

    if normalized is not None and not is_valid_url(normalized):
        normalized = None

    return Candidate(platform=platform, url=url, source=source, confidence=confidence, normalized_url=normalized)
