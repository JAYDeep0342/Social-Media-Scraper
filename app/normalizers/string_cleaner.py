"""General-purpose text cleaning beyond basic whitespace collapsing."""

import re

from app.utils.string_helper import clean_whitespace

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_control_characters(text: str) -> str:
    return _CONTROL_CHARS_RE.sub("", text)


def clean_text(text: str) -> str:
    return clean_whitespace(strip_control_characters(text))
