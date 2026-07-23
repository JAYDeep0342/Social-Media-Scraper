from app.enrichment.social.confidence import Confidence
from app.selection.candidate import make_candidate
from app.selection.engine import SelectionEngine
from app.selection.metrics import SelectionMetrics


def test_selects_exactly_one_url_per_platform() -> None:
    candidates = [
        make_candidate(platform="instagram", url="https://www.instagram.com/biz", source="json_ld", confidence=Confidence.HIGH),
        make_candidate(platform="instagram", url="https://www.instagram.com/biz/reels", source="search_fallback", confidence=Confidence.LOW),
        make_candidate(platform="facebook", url="https://www.facebook.com/biz", source="footer", confidence=Confidence.HIGH),
    ]
    result = SelectionEngine().select(candidates)
    assert result.instagram_url == "https://www.instagram.com/biz"
    assert result.facebook_url == "https://www.facebook.com/biz"


def test_platform_with_no_candidates_yields_none() -> None:
    candidates = [
        make_candidate(platform="instagram", url="https://www.instagram.com/biz", source="footer", confidence=Confidence.HIGH),
    ]
    result = SelectionEngine().select(candidates)
    assert result.instagram_url == "https://www.instagram.com/biz"
    assert result.facebook_url is None


def test_no_candidates_at_all_yields_both_none() -> None:
    result = SelectionEngine().select([])
    assert result.instagram_url is None
    assert result.facebook_url is None


def test_picks_highest_ranked_among_multiple_valid_candidates() -> None:
    candidates = [
        make_candidate(platform="instagram", url="https://www.instagram.com/biz/reels", source="search_fallback", confidence=Confidence.LOW),
        make_candidate(platform="instagram", url="https://www.instagram.com/biz", source="anchor", confidence=Confidence.HIGH),
        make_candidate(platform="instagram", url="https://www.instagram.com/otherbiz", source="search_fallback", confidence=Confidence.MEDIUM),
    ]
    result = SelectionEngine().select(candidates)
    assert result.instagram_url == "https://www.instagram.com/biz"


def test_malformed_candidates_are_ignored_not_selected() -> None:
    candidates = [make_candidate(platform="instagram", url="not a url", source="anchor", confidence=Confidence.HIGH)]
    result = SelectionEngine().select(candidates)
    assert result.instagram_url is None


def test_metrics_are_recorded_end_to_end() -> None:
    candidates = [
        make_candidate(platform="instagram", url="https://www.instagram.com/biz", source="json_ld", confidence=Confidence.HIGH),
        make_candidate(platform="instagram", url="https://www.instagram.com/biz/", source="anchor", confidence=Confidence.HIGH),  # dup
        make_candidate(platform="facebook", url="not a url", source="anchor", confidence=Confidence.LOW),  # rejected
    ]
    metrics = SelectionMetrics()
    result = SelectionEngine().select(candidates, metrics=metrics)

    snapshot = metrics.snapshot()
    assert snapshot.candidates == 3
    assert snapshot.duplicates == 1
    assert snapshot.rejected == 1
    assert snapshot.selected == 1  # only instagram was found
    assert result.facebook_url is None
