"""Classifies a discovered social link's confidence:

- HIGH: found directly on the business's own official website.
- MEDIUM: found via search fallback, and the URL matches a clean,
  canonical profile shape (e.g. https://www.instagram.com/<handle>/ with
  no extra path segments).
- LOW: found via search fallback with a weaker/non-canonical URL shape.
"""

import re
from enum import Enum
from typing import Optional


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


_CANONICAL_INSTAGRAM_RE = re.compile(r"^https://www\.instagram\.com/([A-Za-z0-9_.]{1,30})/?$")
_CANONICAL_FACEBOOK_RE = re.compile(r"^https://www\.facebook\.com/([A-Za-z0-9.\-]{1,100})/?$")

_FACEBOOK_NON_PROFILE_SLUGS = {
    "groups",
    "events",
    "watch",
    "marketplace",
    "permalink.php",
    "sharer",
    "sharer.php",
    "pages",
}


def canonical_slug(url: str, platform: str) -> Optional[str]:
    """Returns the profile slug if `url` is a clean canonical profile URL
    for `platform`, else None (e.g. a sub-page, hashtag, or post link)."""
    if platform == "instagram":
        match = _CANONICAL_INSTAGRAM_RE.match(url)
        return match.group(1) if match else None

    if platform == "facebook":
        if url.startswith("https://www.facebook.com/profile.php?id="):
            return url.rsplit("id=", 1)[-1]
        match = _CANONICAL_FACEBOOK_RE.match(url)
        if match and match.group(1).lower() not in _FACEBOOK_NON_PROFILE_SLUGS:
            return match.group(1)
        return None

    return None


def is_canonical_social_url(url: str, platform: str) -> bool:
    return canonical_slug(url, platform) is not None


def classify_confidence(*, url: Optional[str], found_on_website: bool, platform: Optional[str] = None) -> Confidence:
    if url is None:
        return Confidence.NONE
    if found_on_website:
        return Confidence.HIGH
    if platform and is_canonical_social_url(url, platform):
        return Confidence.MEDIUM
    return Confidence.LOW
