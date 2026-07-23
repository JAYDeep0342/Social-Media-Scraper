"""Generic string helpers shared by future extractors/parsers."""

import re
import unicodedata
from typing import Any, Optional


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)


def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)].rstrip() + suffix


def safe_str(value: Optional[Any], default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()
