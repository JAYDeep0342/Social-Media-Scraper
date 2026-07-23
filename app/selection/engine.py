"""Top-level selection engine: given a business's raw candidate URLs
(gathered from any prior discovery/enrichment phase), returns exactly one
Instagram URL and one Facebook URL — the best-ranked, deduplicated
candidate per platform — or None for a platform with no valid candidate
at all (there is no URL to fabricate).
"""

from dataclasses import dataclass
from typing import List, Optional

from app.selection.candidate import Candidate
from app.selection.dedup import deduplicate
from app.selection.metrics import SelectionMetrics
from app.selection.ranking import SocialUrlRanker

_PLATFORMS = ("instagram", "facebook")


@dataclass
class SelectionResult:
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None


class SelectionEngine:
    def __init__(self, ranker: Optional[SocialUrlRanker] = None) -> None:
        self._ranker = ranker or SocialUrlRanker()

    def select(self, candidates: List[Candidate], *, metrics: Optional[SelectionMetrics] = None) -> SelectionResult:
        if metrics is not None:
            metrics.record_candidates(len(candidates))

        rejected_count = sum(1 for c in candidates if not c.normalized_url)
        if metrics is not None and rejected_count:
            metrics.record_rejected(rejected_count)

        deduped, duplicate_count = deduplicate(candidates)
        if metrics is not None and duplicate_count:
            metrics.record_duplicates(duplicate_count)

        usable = [c for c in deduped if c.normalized_url]
        result = SelectionResult()

        for platform in _PLATFORMS:
            platform_candidates = [c for c in usable if c.platform == platform]
            if not platform_candidates:
                continue
            best = self._ranker.rank(platform_candidates)[0]
            setattr(result, f"{platform}_url", best.normalized_url)

        selected_count = sum(1 for url in (result.instagram_url, result.facebook_url) if url)
        if metrics is not None and selected_count:
            metrics.record_selected(selected_count)

        return result
