"""Generic structural validation for dict-like responses/payloads, useful
for verifying a future extractor/parser produced the fields it promised."""

from typing import Any, Iterable

from app.exceptions.errors import ValidationError


def validate_required_fields(data: dict[str, Any], required: Iterable[str]) -> None:
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise ValidationError("Missing required fields", details={"missing_fields": missing})
