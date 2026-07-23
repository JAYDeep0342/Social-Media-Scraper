"""Normalizes free-form location text into a consistent 'Part, Part' shape,
e.g. '  austin,tx ' -> 'Austin, Tx'."""

from app.utils.string_helper import clean_whitespace


def normalize_location(location: str) -> str:
    parts = [clean_whitespace(part).title() for part in location.split(",") if clean_whitespace(part)]
    return ", ".join(parts)
