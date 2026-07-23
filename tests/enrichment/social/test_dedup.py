from app.enrichment.social.dedup import deduplicate_candidates
from app.enrichment.social.link_extractor import LinkCandidate


def test_removes_exact_duplicate() -> None:
    candidates = [
        LinkCandidate(url="https://www.instagram.com/biz", platform="instagram", source="footer"),
        LinkCandidate(url="https://www.instagram.com/biz", platform="instagram", source="anchor"),
    ]
    unique = deduplicate_candidates(candidates)
    assert len(unique) == 1
    assert unique[0].source == "footer"  # first occurrence kept


def test_removes_duplicates_that_only_match_after_normalization() -> None:
    candidates = [
        LinkCandidate(url="https://m.facebook.com/biz?fbclid=abc", platform="facebook", source="anchor"),
        LinkCandidate(url="https://www.facebook.com/biz", platform="facebook", source="footer"),
    ]
    unique = deduplicate_candidates(candidates)
    assert len(unique) == 1


def test_keeps_genuinely_different_urls() -> None:
    candidates = [
        LinkCandidate(url="https://www.instagram.com/biz1", platform="instagram", source="footer"),
        LinkCandidate(url="https://www.instagram.com/biz2", platform="instagram", source="header"),
    ]
    unique = deduplicate_candidates(candidates)
    assert len(unique) == 2


def test_empty_input_returns_empty_list() -> None:
    assert deduplicate_candidates([]) == []
