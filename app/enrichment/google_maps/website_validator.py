"""Validates and normalizes a website URL extracted from a Google Maps
detail panel. A thin wrapper composing the existing generic validator/
normalizer (Phase 1.1) rather than reimplementing URL handling.
"""

from typing import Optional

from app.exceptions.errors import ValidationError
from app.normalizers.url_normalizer import normalize_business_url
from app.validators.url_validator import validate_url


def validate_and_normalize_website(raw_url: Optional[str]) -> Optional[str]:
    """Returns a validated, normalized website URL, or None if `raw_url` is
    falsy or not a well-formed http(s) URL.

    Never raises: a business whose listed website is malformed is treated
    as having no usable website rather than failing the whole enrichment.
    """
    if not raw_url:
        return None
    try:
        validate_url(raw_url, field_name="website")
    except ValidationError:
        return None
    return normalize_business_url(raw_url)
