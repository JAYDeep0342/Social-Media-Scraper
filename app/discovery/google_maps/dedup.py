"""Deduplicates BusinessLead results by Google Maps URL.

Google Maps place URLs embed a stable place identifier (the `!1s<hex>:<hex>`
segment, commonly called the CID) that stays the same even if surrounding
query parameters differ between renders. When present, that identifier is
used as the dedup key; otherwise the URL's path (without query string) is
used as a fallback.
"""

import re
from typing import Iterable, List, Optional, Tuple

from app.models.domain import BusinessLead

_PLACE_ID_RE = re.compile(r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)")


def extract_place_id(maps_url: str) -> Optional[str]:
    match = _PLACE_ID_RE.search(maps_url)
    return match.group(1) if match else None


def _dedup_key(maps_url: str) -> str:
    return extract_place_id(maps_url) or maps_url.split("?", 1)[0].rstrip("/")


def deduplicate_leads(leads: Iterable[BusinessLead]) -> Tuple[List[BusinessLead], int]:
    """Returns (deduplicated leads, duplicate count removed), keeping the
    first occurrence of each distinct Google Maps URL."""
    seen: set[str] = set()
    unique: List[BusinessLead] = []
    duplicate_count = 0

    for lead in leads:
        maps_url = lead.social.google_maps_url
        if not maps_url:
            unique.append(lead)  # nothing to dedupe on; keep it
            continue

        key = _dedup_key(maps_url)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        unique.append(lead)

    return unique, duplicate_count
