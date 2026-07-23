from app.enrichment.social.confidence import Confidence, canonical_slug, classify_confidence, is_canonical_social_url


def test_canonical_instagram_url() -> None:
    assert canonical_slug("https://www.instagram.com/starbucks/", "instagram") == "starbucks"
    assert canonical_slug("https://www.instagram.com/starbucks", "instagram") == "starbucks"


def test_non_canonical_instagram_subpage_is_rejected() -> None:
    assert canonical_slug("https://www.instagram.com/starbucks/reels/", "instagram") is None
    assert canonical_slug("https://www.instagram.com/p/abc123/", "instagram") is None


def test_canonical_facebook_url() -> None:
    assert canonical_slug("https://www.facebook.com/starbucks", "facebook") == "starbucks"


def test_facebook_profile_php_is_canonical() -> None:
    assert canonical_slug("https://www.facebook.com/profile.php?id=12345", "facebook") == "12345"


def test_facebook_non_profile_paths_are_rejected() -> None:
    assert canonical_slug("https://www.facebook.com/groups", "facebook") is None
    assert canonical_slug("https://www.facebook.com/events", "facebook") is None


def test_is_canonical_social_url_wraps_canonical_slug() -> None:
    assert is_canonical_social_url("https://www.instagram.com/starbucks/", "instagram") is True
    assert is_canonical_social_url("https://www.instagram.com/starbucks/reels/", "instagram") is False


def test_classify_confidence_high_when_found_on_website() -> None:
    result = classify_confidence(url="https://www.instagram.com/anything", found_on_website=True)
    assert result == Confidence.HIGH


def test_classify_confidence_medium_when_canonical_via_fallback() -> None:
    result = classify_confidence(
        url="https://www.instagram.com/starbucks/", found_on_website=False, platform="instagram"
    )
    assert result == Confidence.MEDIUM


def test_classify_confidence_low_when_non_canonical_via_fallback() -> None:
    result = classify_confidence(
        url="https://www.instagram.com/starbucks/reels/", found_on_website=False, platform="instagram"
    )
    assert result == Confidence.LOW


def test_classify_confidence_none_when_no_url() -> None:
    assert classify_confidence(url=None, found_on_website=False) == Confidence.NONE
