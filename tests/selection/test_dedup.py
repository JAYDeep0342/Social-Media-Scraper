from app.enrichment.social.confidence import Confidence
from app.selection.candidate import make_candidate
from app.selection.dedup import deduplicate


def test_merges_exact_duplicate() -> None:
    a = make_candidate(platform="instagram", url="https://www.instagram.com/biz", source="anchor", confidence=Confidence.HIGH)
    b = make_candidate(platform="instagram", url="https://www.instagram.com/biz", source="footer", confidence=Confidence.HIGH)
    unique, duplicate_count = deduplicate([a, b])
    assert len(unique) == 1
    assert duplicate_count == 1


def test_merges_duplicates_that_only_match_after_normalization() -> None:
    a = make_candidate(platform="facebook", url="https://m.facebook.com/biz?fbclid=abc", source="anchor", confidence=Confidence.HIGH)
    b = make_candidate(platform="facebook", url="https://www.facebook.com/biz/", source="footer", confidence=Confidence.HIGH)
    unique, duplicate_count = deduplicate([a, b])
    assert len(unique) == 1
    assert duplicate_count == 1


def test_keeps_the_better_ranked_duplicate() -> None:
    weak_source = make_candidate(platform="instagram", url="https://www.instagram.com/biz", source="anchor", confidence=Confidence.HIGH)
    strong_source = make_candidate(platform="instagram", url="https://www.instagram.com/biz", source="json_ld", confidence=Confidence.HIGH)
    unique, _ = deduplicate([weak_source, strong_source])
    assert len(unique) == 1
    assert unique[0].source == "json_ld"


def test_keeps_genuinely_different_urls() -> None:
    a = make_candidate(platform="instagram", url="https://www.instagram.com/biz1", source="anchor", confidence=Confidence.HIGH)
    b = make_candidate(platform="instagram", url="https://www.instagram.com/biz2", source="anchor", confidence=Confidence.HIGH)
    unique, duplicate_count = deduplicate([a, b])
    assert len(unique) == 2
    assert duplicate_count == 0


def test_different_platforms_with_same_normalized_url_are_not_merged() -> None:
    # Contrived, but the dedup key must include platform, not just the URL.
    a = make_candidate(platform="instagram", url="https://www.instagram.com/biz", source="anchor", confidence=Confidence.HIGH)
    b = make_candidate(platform="facebook", url="https://www.instagram.com/biz", source="anchor", confidence=Confidence.HIGH)
    unique, duplicate_count = deduplicate([a, b])
    assert len(unique) == 2
    assert duplicate_count == 0


def test_unnormalizable_candidates_pass_through_untouched() -> None:
    bad = make_candidate(platform="facebook", url="not a url", source="anchor", confidence=Confidence.LOW)
    unique, duplicate_count = deduplicate([bad])
    assert unique == [bad]
    assert duplicate_count == 0


def test_empty_input_returns_empty_list() -> None:
    assert deduplicate([]) == ([], 0)
