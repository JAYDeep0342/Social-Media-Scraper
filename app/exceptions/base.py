"""Base application exception. All domain exceptions inherit from this so a
single FastAPI exception handler can catch them uniformly."""

from typing import Any, Optional


class AppException(Exception):
    status_code: int = 500

    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"error": self.__class__.__name__, "message": self.message, "details": self.details}
