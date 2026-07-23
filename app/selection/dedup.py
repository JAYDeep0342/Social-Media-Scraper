"""Deduplicates candidates by (platform, normalized_url), keeping the
highest-ranked duplicate rather than an arbitrary first-seen one.

Tracking-param stripping, trailing-slash removal, and domain
normalization already happened when each Candidate's `normalized_url` was
computed (see app.selection.candidate.make_candidate, which reuses
app.enrichment.social.url_normalizer) — this step only merges the results.
"""

from typing import Dict, List, Tuple

from app.selection.candidate import Candidate
from app.selection.ranking import rank_score


def deduplicate(candidates: List[Candidate]) -> Tuple[List[Candidate], int]:
    """Returns (deduplicated candidates, duplicate_count). Candidates
    without a usable normalized_url are passed through untouched — they
    are not "duplicates," they're the caller's problem to reject."""
    best_by_key: Dict[Tuple[str, str], Candidate] = {}
    unnormalizable: List[Candidate] = []
    duplicate_count = 0

    for candidate in candidates:
        if not candidate.normalized_url:
            unnormalizable.append(candidate)
            continue

        key = (candidate.platform, candidate.normalized_url)
        existing = best_by_key.get(key)
        if existing is None:
            best_by_key[key] = candidate
        else:
            duplicate_count += 1
            if rank_score(candidate) > rank_score(existing):
                best_by_key[key] = candidate

    return [*best_by_key.values(), *unnormalizable], duplicate_count
