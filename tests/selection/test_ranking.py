import pytest

from app.enrichment.social.confidence import Confidence
from app.ranking.base import Ranker
from app.selection.candidate import make_candidate
from app.selection.ranking import SocialUrlRanker, rank_score


def test_higher_confidence_outranks_lower_confidence() -> None:
    high = make_candidate(platform="instagram", url="https://www.instagram.com/a", source="anchor", confidence=Confidence.HIGH)
    low = make_candidate(platform="instagram", url="https://www.instagram.com/b", source="anchor", confidence=Confidence.LOW)
    assert rank_score(high) > rank_score(low)


def test_source_breaks_ties_within_same_confidence() -> None:
    json_ld = make_candidate(platform="instagram", url="https://www.instagram.com/a", source="json_ld", confidence=Confidence.HIGH)
    anchor = make_candidate(platform="instagram", url="https://www.instagram.com/a", source="anchor", confidence=Confidence.HIGH)
    assert rank_score(json_ld) > rank_score(anchor)


def test_canonical_url_outranks_non_canonical_at_same_confidence() -> None:
    canonical = make_candidate(platform="instagram", url="https://www.instagram.com/mybiz", source="search_fallback", confidence=Confidence.LOW)
    subpage = make_candidate(platform="instagram", url="https://www.instagram.com/mybiz/reels", source="search_fallback", confidence=Confidence.LOW)
    assert rank_score(canonical) > rank_score(subpage)


def test_clean_url_outranks_url_with_a_surviving_query_param() -> None:
    clean = make_candidate(platform="facebook", url="https://www.facebook.com/mybiz", source="anchor", confidence=Confidence.HIGH)
    # "locale" isn't in the stripped tracking-param set, so it survives
    # normalization and should be penalized by the cleanliness score.
    messy = make_candidate(platform="facebook", url="https://www.facebook.com/mybiz?locale=en_US", source="anchor", confidence=Confidence.HIGH)
    assert rank_score(clean) > rank_score(messy)


def test_unnormalizable_candidate_scores_zero() -> None:
    bad = make_candidate(platform="facebook", url="not a url", source="anchor", confidence=Confidence.HIGH)
    assert rank_score(bad) == 0.0


def test_social_url_ranker_is_a_ranker() -> None:
    assert isinstance(SocialUrlRanker(), Ranker)


def test_social_url_ranker_sorts_best_first() -> None:
    high = make_candidate(platform="instagram", url="https://www.instagram.com/a", source="json_ld", confidence=Confidence.HIGH)
    low = make_candidate(platform="instagram", url="https://www.instagram.com/b", source="search_fallback", confidence=Confidence.LOW)
    ranked = SocialUrlRanker().rank([low, high])
    assert ranked == [high, low]


def test_ranker_abc_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        Ranker()
