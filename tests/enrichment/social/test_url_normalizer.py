from app.enrichment.social.url_normalizer import normalize_social_url


def test_bare_domain_gets_https_and_www() -> None:
    assert normalize_social_url("instagram.com/mybiz") == "https://www.instagram.com/mybiz"


def test_mobile_facebook_domain_is_canonicalized() -> None:
    assert normalize_social_url("https://m.facebook.com/mybiz") == "https://www.facebook.com/mybiz"
    assert normalize_social_url("https://mobile.facebook.com/mybiz") == "https://www.facebook.com/mybiz"
    assert normalize_social_url("https://facebook.com/mybiz") == "https://www.facebook.com/mybiz"


def test_http_is_upgraded_to_https() -> None:
    assert normalize_social_url("http://www.instagram.com/mybiz") == "https://www.instagram.com/mybiz"


def test_tracking_params_are_stripped() -> None:
    result = normalize_social_url("https://www.instagram.com/mybiz?igshid=abc123")
    assert "igshid" not in result

    result = normalize_social_url("https://www.facebook.com/mybiz?fbclid=xyz")
    assert "fbclid" not in result


def test_facebook_link_shim_is_unwrapped() -> None:
    wrapped = "https://l.facebook.com/l.php?u=https%3A%2F%2Fwww.facebook.com%2Fmybiz&h=abc"
    assert normalize_social_url(wrapped) == "https://www.facebook.com/mybiz"


def test_same_profile_different_forms_normalize_identically() -> None:
    a = normalize_social_url("https://m.facebook.com/mybiz?fbclid=abc")
    b = normalize_social_url("facebook.com/mybiz")
    assert a == b
