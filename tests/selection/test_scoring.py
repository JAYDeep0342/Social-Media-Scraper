from app.enrichment.social.confidence import Confidence
from app.selection.scoring import confidence_score


def test_high_scores_100() -> None:
    assert confidence_score(Confidence.HIGH) == 100


def test_medium_scores_70() -> None:
    assert confidence_score(Confidence.MEDIUM) == 70


def test_low_scores_40() -> None:
    assert confidence_score(Confidence.LOW) == 40


def test_none_scores_0() -> None:
    assert confidence_score(Confidence.NONE) == 0


def test_ordering_is_high_gt_medium_gt_low_gt_none() -> None:
    assert confidence_score(Confidence.HIGH) > confidence_score(Confidence.MEDIUM)
    assert confidence_score(Confidence.MEDIUM) > confidence_score(Confidence.LOW)
    assert confidence_score(Confidence.LOW) > confidence_score(Confidence.NONE)
