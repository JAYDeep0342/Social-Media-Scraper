"""URL confidence & dedup engine: takes social URL candidates already
collected by earlier phases (Phase 3-5) and picks exactly one Instagram
URL and one Facebook URL per business. Pure in-memory computation — no
scraping, no HTTP requests, no platform access of any kind.
"""

from app.selection.candidate import Candidate, make_candidate
from app.selection.dedup import deduplicate
from app.selection.engine import SelectionEngine, SelectionResult
from app.selection.metrics import SelectionMetrics, SelectionMetricsSnapshot
from app.selection.ranking import SocialUrlRanker, rank_score
from app.selection.scoring import confidence_score

__all__ = [
    "Candidate",
    "make_candidate",
    "confidence_score",
    "rank_score",
    "SocialUrlRanker",
    "deduplicate",
    "SelectionEngine",
    "SelectionResult",
    "SelectionMetrics",
    "SelectionMetricsSnapshot",
]
