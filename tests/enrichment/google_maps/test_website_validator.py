from app.enrichment.google_maps.website_validator import validate_and_normalize_website


def test_none_input_returns_none() -> None:
    assert validate_and_normalize_website(None) is None


def test_empty_string_returns_none() -> None:
    assert validate_and_normalize_website("") is None


def test_valid_bare_domain_is_normalized() -> None:
    assert validate_and_normalize_website("storyville.com") == "https://storyville.com"


def test_valid_full_url_is_kept() -> None:
    assert validate_and_normalize_website("https://storyville.com/pages/pike-place") == (
        "https://storyville.com/pages/pike-place"
    )


def test_malformed_url_returns_none_without_raising() -> None:
    assert validate_and_normalize_website("not a url") is None


def test_tracking_params_are_stripped() -> None:
    result = validate_and_normalize_website("https://storyville.com/?utm_source=maps")
    assert "utm_source" not in result
