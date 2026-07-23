"""Generic URL validation, raising the app's domain ValidationError instead
of returning a bare bool, so callers get a consistent error shape."""

from app.exceptions.errors import ValidationError
from app.utils.url_helper import is_valid_url, normalize_url


def validate_url(value: str, *, field_name: str = "url") -> str:
    """Normalize and validate `value`. Returns the normalized URL, or raises
    ValidationError if it isn't a well-formed http(s) URL."""
    normalized = normalize_url(value)
    if not is_valid_url(normalized):
        raise ValidationError(
            f"'{value}' is not a valid {field_name}",
            details={"field": field_name, "value": value},
        )
    return normalized
