import pytest

from app.exceptions.errors import ValidationError
from app.validators.response_validator import validate_required_fields
from app.validators.search_validator import validate_search_request
from app.validators.url_validator import validate_url


def test_validate_url_normalizes_and_passes() -> None:
    assert validate_url("example.com") == "https://example.com"


def test_validate_url_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        validate_url("not a url", field_name="website")


def test_validate_search_request_accepts_valid_payload() -> None:
    request = validate_search_request({"keyword": "plumbers", "location": "Austin, TX"})
    assert request.keyword == "plumbers"
    assert request.limit == 20


def test_validate_search_request_rejects_invalid_payload() -> None:
    with pytest.raises(ValidationError):
        validate_search_request({"keyword": "", "location": "Austin"})


def test_validate_required_fields_passes_when_present() -> None:
    validate_required_fields({"business_name": "Acme"}, ["business_name"])


def test_validate_required_fields_raises_when_missing() -> None:
    with pytest.raises(ValidationError):
        validate_required_fields({"business_name": ""}, ["business_name", "website"])
