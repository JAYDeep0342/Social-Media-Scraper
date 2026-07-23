"""Concrete domain exceptions used across the scraping pipeline."""

from app.exceptions.base import AppException


class ConfigurationError(AppException):
    """Raised when required configuration is missing or invalid."""

    status_code = 500


class DiscoveryError(AppException):
    """Raised when a discovery step (finding candidate leads) fails."""

    status_code = 502


class ExtractionError(AppException):
    """Raised when extracting structured data from a source fails."""

    status_code = 502


class ScraperTimeoutError(AppException):
    """Raised when a scraping operation exceeds its allotted time budget.

    Named `ScraperTimeoutError` rather than `TimeoutError` to avoid shadowing
    Python's builtin `TimeoutError` / `asyncio.TimeoutError`.
    """

    status_code = 504


class ValidationError(AppException):
    """Raised when input or extracted data fails validation."""

    status_code = 422
