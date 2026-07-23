"""Bridges Pydantic's SearchRequest validation into the app's domain
exception system, so callers only ever need to catch ValidationError."""

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.exceptions.errors import ValidationError
from app.schemas.search import SearchRequest


def validate_search_request(data: dict[str, Any]) -> SearchRequest:
    try:
        return SearchRequest(**data)
    except PydanticValidationError as exc:
        raise ValidationError("Invalid search request", details={"errors": exc.errors()}) from exc
