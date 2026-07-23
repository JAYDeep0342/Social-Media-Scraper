"""Converts the HIGH/MEDIUM/LOW/NONE confidence tier into a numeric score
for ranking arithmetic (e.g. HIGH=100, MEDIUM=70, LOW=40), sourced from
settings so operators can retune without a code change.
"""

from app.config.settings import get_settings
from app.enrichment.social.confidence import Confidence


def confidence_score(confidence: Confidence) -> int:
    settings = get_settings()
    scores = {
        Confidence.HIGH: settings.CONFIDENCE_SCORE_HIGH,
        Confidence.MEDIUM: settings.CONFIDENCE_SCORE_MEDIUM,
        Confidence.LOW: settings.CONFIDENCE_SCORE_LOW,
        Confidence.NONE: settings.CONFIDENCE_SCORE_NONE,
    }
    return scores.get(confidence, settings.CONFIDENCE_SCORE_NONE)
