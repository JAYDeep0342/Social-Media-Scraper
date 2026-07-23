"""Multi-factor URL ranking: confidence, source reliability, canonical
shape, domain quality, and URL cleanliness combine into one composite
score used to pick the best candidate per platform.

Activates the Phase 1.1 `Ranker` interface (app.ranking.base), which was
architecture-only until now.
"""

from typing import Sequence
from urllib.parse import urlparse

from app.enrichment.social.confidence import canonical_slug
from app.ranking.base import Ranker
from app.selection.candidate import Candidate
from app.selection.scoring import confidence_score

# Source reliability: structured/curated signals (schema.org markup,
# rel=me, footer/header nav) outrank a loose body anchor or a
# search-engine guess, independent of confidence tier. Values match
# app.enrichment.social.link_extractor.LinkCandidate.source exactly, plus
# "search_fallback" for a URL found via app.enrichment.social.search_fallback.
_SOURCE_WEIGHTS = {
    "json_ld": 15,
    "meta": 15,
    "footer": 10,
    "header": 10,
    "anchor": 5,
    "search_fallback": 0,
}

_CANONICAL_DOMAINS = {"instagram": "www.instagram.com", "facebook": "www.facebook.com"}

_CANONICAL_BONUS = 20
_DOMAIN_QUALITY_BONUS = 10
_CLEAN_QUERY_BONUS = 5
_CLEAN_PATH_BONUS = 5


def _source_weight(source: str) -> int:
    return _SOURCE_WEIGHTS.get(source, 0)


def _canonical_bonus(candidate: Candidate) -> int:
    if not candidate.normalized_url:
        return 0
    return _CANONICAL_BONUS if canonical_slug(candidate.normalized_url, candidate.platform) else 0


def _domain_quality_score(candidate: Candidate) -> int:
    if not candidate.normalized_url:
        return 0
    expected = _CANONICAL_DOMAINS.get(candidate.platform)
    return _DOMAIN_QUALITY_BONUS if urlparse(candidate.normalized_url).netloc == expected else 0


def _cleanliness_score(candidate: Candidate) -> int:
    if not candidate.normalized_url:
        return 0
    parsed = urlparse(candidate.normalized_url)
    score = 0
    if not parsed.query:
        score += _CLEAN_QUERY_BONUS
    path_segments = [seg for seg in parsed.path.split("/") if seg]
    if len(path_segments) <= 1:
        score += _CLEAN_PATH_BONUS
    return score


def rank_score(candidate: Candidate) -> float:
    """Higher is better. A candidate with no usable normalized_url always
    scores 0 regardless of confidence — it can't be selected."""
    if not candidate.normalized_url:
        return 0.0
    return (
        confidence_score(candidate.confidence)
        + _source_weight(candidate.source)
        + _canonical_bonus(candidate)
        + _domain_quality_score(candidate)
        + _cleanliness_score(candidate)
    )


class SocialUrlRanker(Ranker[Candidate]):
    name = "social_url_ranker"

    def rank(self, items: Sequence[Candidate]) -> list[Candidate]:
        return sorted(items, key=rank_score, reverse=True)
