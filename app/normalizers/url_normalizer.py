"""URL normalization for lead deduplication: base normalization plus
stripping common marketing/tracking query parameters."""

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.utils.url_helper import normalize_url

_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}


def normalize_business_url(url: str) -> str:
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    clean_query = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in _TRACKING_PARAMS]
    return urlunparse(parsed._replace(query=urlencode(clean_query)))
