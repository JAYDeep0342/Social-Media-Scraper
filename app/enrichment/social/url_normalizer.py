"""Normalizes Instagram/Facebook URLs found during social discovery:

- canonicalizes mobile-domain variants (m.facebook.com, mobile.facebook.com,
  bare instagram.com/facebook.com) to a single `www.` form
- forces https
- unwraps Facebook's link-shim redirect (`l.facebook.com/l.php?u=...`) — a
  pure string/query-decode operation, since the target is already encoded
  in the URL itself; no HTTP request is made to resolve it (consistent
  with never opening Facebook/Instagram directly)
- strips tracking query parameters, reusing the generic normalizer from
  Phase 1.1 and extending it with Instagram/Facebook-specific ones
"""

from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

from app.normalizers.url_normalizer import normalize_business_url
from app.utils.url_helper import normalize_url

_SOCIAL_TRACKING_PARAMS = {
    "igshid",
    "igsh",
    "fbclid",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "ref",
    "hc_ref",
    "__tn__",
}

_MOBILE_HOSTS = {
    "facebook.com": "www.facebook.com",
    "m.facebook.com": "www.facebook.com",
    "mobile.facebook.com": "www.facebook.com",
    "instagram.com": "www.instagram.com",
}


def _unwrap_facebook_link_shim(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower() == "l.facebook.com" and parsed.path == "/l.php":
        target = parse_qs(parsed.query).get("u")
        if target:
            return target[0]
    return url


def _canonicalize_domain(url: str) -> str:
    parsed = urlparse(url)
    canonical_host = _MOBILE_HOSTS.get(parsed.netloc.lower())
    if canonical_host:
        parsed = parsed._replace(netloc=canonical_host)
    if parsed.scheme == "http":
        parsed = parsed._replace(scheme="https")
    return urlunparse(parsed)


def _strip_social_tracking_params(url: str) -> str:
    parsed = urlparse(url)
    clean_query = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in _SOCIAL_TRACKING_PARAMS]
    return urlunparse(parsed._replace(query=urlencode(clean_query)))


def normalize_social_url(raw_url: str) -> str:
    url = normalize_url(raw_url)  # ensures a scheme so urlparse resolves netloc reliably
    url = _unwrap_facebook_link_shim(url)
    url = _canonicalize_domain(url)
    url = normalize_business_url(url)  # base normalization + generic utm/fbclid stripping
    url = _strip_social_tracking_params(url)
    return url
