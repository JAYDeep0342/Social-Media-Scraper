"""Extracts Instagram/Facebook URLs from a business homepage's HTML —
anchors, `<link rel="me">` tags, JSON-LD `sameAs` entries, and specifically
within `<footer>`/`<header>` regions. Only URL strings are read; nothing
about the linked profile itself (content, followers, username) is ever
touched, and Instagram/Facebook pages are never opened.
"""

import json
import re
from dataclasses import dataclass
from typing import List, Optional, Set

from bs4 import BeautifulSoup

# Requires a non-empty path segment after the domain (a handle/profile),
# so a bare "instagram.com" / "facebook.com" link -- a generic, unwired
# "follow us" template icon, not a real profile -- is never treated as a
# discovered candidate.
_INSTAGRAM_RE = re.compile(r"(^|//)(www\.)?instagram\.com/[^/?#\s]+", re.IGNORECASE)
_FACEBOOK_RE = re.compile(r"(^|//)(www\.|m\.|mobile\.)?facebook\.com/[^/?#\s]+", re.IGNORECASE)


@dataclass
class LinkCandidate:
    url: str
    platform: str  # "instagram" | "facebook"
    source: str  # "anchor" | "meta" | "json_ld" | "footer" | "header"


def classify_platform(url: str) -> Optional[str]:
    if _INSTAGRAM_RE.search(url):
        return "instagram"
    if _FACEBOOK_RE.search(url):
        return "facebook"
    return None


class SocialLinkExtractor:
    def extract(self, html: str) -> List[LinkCandidate]:
        soup = BeautifulSoup(html, "html.parser")
        candidates: List[LinkCandidate] = []
        seen_urls: Set[str] = set()

        def add(url: str, platform: str, source: str) -> None:
            if url in seen_urls:
                return
            seen_urls.add(url)
            candidates.append(LinkCandidate(url=url, platform=platform, source=source))

        # Footer/header get priority labeling — checked first so a link
        # that lives in one of them isn't relabeled "anchor" by the
        # site-wide sweep below.
        footer = soup.find("footer")
        if footer is not None:
            for anchor in footer.find_all("a", href=True):
                platform = classify_platform(anchor["href"])
                if platform:
                    add(anchor["href"], platform, "footer")

        header = soup.find("header")
        if header is not None:
            for anchor in header.find_all("a", href=True):
                platform = classify_platform(anchor["href"])
                if platform:
                    add(anchor["href"], platform, "header")

        for anchor in soup.find_all("a", href=True):
            platform = classify_platform(anchor["href"])
            if platform:
                add(anchor["href"], platform, "anchor")

        for link in soup.find_all("link", rel="me", href=True):
            platform = classify_platform(link["href"])
            if platform:
                add(link["href"], platform, "meta")

        for script in soup.find_all("script", type="application/ld+json"):
            for url, platform in self._iter_json_ld_same_as(script.string):
                add(url, platform, "json_ld")

        return candidates

    @staticmethod
    def _iter_json_ld_same_as(raw: Optional[str]):
        if not raw:
            return
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return

        items = data if isinstance(data, list) else [data]
        expanded = []
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                expanded.extend(item["@graph"])
            else:
                expanded.append(item)

        for item in expanded:
            if not isinstance(item, dict):
                continue
            same_as = item.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            if not isinstance(same_as, list):
                continue
            for url in same_as:
                if not isinstance(url, str):
                    continue
                platform = classify_platform(url)
                if platform:
                    yield url, platform
