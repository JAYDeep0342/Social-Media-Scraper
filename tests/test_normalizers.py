from app.normalizers.business_name_normalizer import normalize_business_name
from app.normalizers.location_normalizer import normalize_location
from app.normalizers.string_cleaner import clean_text
from app.normalizers.url_normalizer import normalize_business_url


def test_normalize_business_name_strips_whitespace_and_punctuation() -> None:
    assert normalize_business_name("  Acme Plumbing -- ") == "Acme Plumbing"


def test_normalize_business_url_strips_tracking_params() -> None:
    result = normalize_business_url("example.com/page?utm_source=fb&id=1")
    assert "utm_source" not in result
    assert "id=1" in result


def test_normalize_location_titlecases_parts() -> None:
    assert normalize_location("  austin,  tx ") == "Austin, Tx"


def test_clean_text_removes_control_characters() -> None:
    assert clean_text("hello\x00\x1f  world") == "hello world"
