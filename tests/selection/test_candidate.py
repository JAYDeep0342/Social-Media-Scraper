from app.enrichment.social.confidence import Confidence
from app.selection.candidate import make_candidate


def test_normalizes_url_on_construction() -> None:
    candidate = make_candidate(
        platform="instagram", url="instagram.com/mybiz", source="anchor", confidence=Confidence.HIGH
    )
    assert candidate.normalized_url == "https://www.instagram.com/mybiz"
    assert candidate.url == "instagram.com/mybiz"  # raw url preserved


def test_strips_tracking_params_on_construction() -> None:
    candidate = make_candidate(
        platform="instagram", url="https://www.instagram.com/mybiz?igshid=abc", source="anchor", confidence=Confidence.HIGH
    )
    assert candidate.normalized_url == "https://www.instagram.com/mybiz"


def test_malformed_url_yields_none_normalized_url() -> None:
    candidate = make_candidate(platform="facebook", url="not a url", source="anchor", confidence=Confidence.LOW)
    assert candidate.normalized_url is None


def test_candidate_is_immutable() -> None:
    candidate = make_candidate(
        platform="instagram", url="https://www.instagram.com/mybiz", source="anchor", confidence=Confidence.HIGH
    )
    try:
        candidate.url = "changed"
        raised = False
    except Exception:
        raised = True
    assert raised, "Candidate should be frozen/immutable"


def test_all_five_fields_are_present() -> None:
    candidate = make_candidate(
        platform="facebook", url="https://www.facebook.com/mybiz", source="footer", confidence=Confidence.HIGH
    )
    assert candidate.platform == "facebook"
    assert candidate.url == "https://www.facebook.com/mybiz"
    assert candidate.source == "footer"
    assert candidate.confidence == Confidence.HIGH
    assert candidate.normalized_url == "https://www.facebook.com/mybiz"
