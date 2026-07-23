"""Normalizes free-form business name text: whitespace and stray leading/
trailing punctuation only — no source-specific formatting rules."""

from app.utils.string_helper import clean_whitespace


def normalize_business_name(name: str) -> str:
    return clean_whitespace(name).strip(" -–—.,")
