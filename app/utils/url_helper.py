"""Generic URL helpers shared by future extractors/parsers."""

import re
from urllib.parse import urlparse, urlunparse

# RFC 1123-style hostname: labels of alnum/hyphen (no leading/trailing hyphen),
# joined by dots. Rejects whitespace and other garbage that a bare netloc
# non-empty check would otherwise let through (e.g. "not a url").
_HOSTNAME_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
    except (ValueError, AttributeError):
        return False

    if result.scheme not in ("http", "https") or not result.netloc:
        return False

    try:
        hostname = result.hostname or ""
    except ValueError:
        return False

    return hostname == "localhost" or ("." in hostname and bool(_HOSTNAME_RE.match(hostname)))


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    normalized = parsed._replace(path=parsed.path.rstrip("/"), fragment="")
    return urlunparse(normalized)


def extract_domain(url: str) -> str:
    parsed = urlparse(url if url.startswith(("http://", "https://")) else f"https://{url}")
    domain = parsed.netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain
