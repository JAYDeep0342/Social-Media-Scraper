"""DuckDuckGo search provider — real implementation via the html-only
endpoint, which requires no JS rendering (unlike Google/Bing's search
UIs). This is the only provider actually implemented among the Phase 1.1
stubs: Google/Bing remain NotImplementedError since scraping their result
pages reliably needs either Playwright or heavy anti-bot handling, which
conflicts with Phase 5's "prefer HTTP requests, avoid Playwright unless
necessary."

Verified live against `https://html.duckduckgo.com/html/`: every result
anchor (`a.result__a`) wraps its target in DuckDuckGo's own redirect,
`//duckduckgo.com/l/?uddg=<url-encoded target>&rut=...`, and the result
list can include ad/tracking entries whose "target" isn't a real page at
all — both are the caller's problem to filter (see
app.enrichment.social.search_fallback), not this provider's.
"""

from typing import Any, List, Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from app.config.constants import DUCKDUCKGO_HTML_ENDPOINT
from app.core.logging import get_logger
from app.network.session_manager import SessionManager
from app.providers.base import SearchProvider

logger = get_logger(__name__)


class DuckDuckGoSearchProvider(SearchProvider):
    name = "duckduckgo"

    def __init__(self, session_manager: Optional[SessionManager] = None) -> None:
        self._session_manager = session_manager

    def _get_session_manager(self) -> SessionManager:
        return self._session_manager or SessionManager.get_instance()

    async def discover(self, keyword: str, location: str, limit: int) -> List[Any]:
        """`keyword` is used as the full literal query string (e.g.
        `site:instagram.com "Business Name"`); `location` is unused by
        this provider. Returns up to `limit` unwrapped result URLs, in
        DuckDuckGo's own ranked order.
        """
        try:
            response = await self._get_session_manager().request(
                "GET", DUCKDUCKGO_HTML_ENDPOINT, params={"q": keyword}
            )
        except Exception:
            logger.warning("DuckDuckGo search failed for query: %s", keyword, exc_info=True)
            return []

        if response.status_code >= 400:
            logger.warning("DuckDuckGo search returned status %s for query: %s", response.status_code, keyword)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        urls: List[str] = []
        for anchor in soup.find_all("a", class_="result__a", href=True):
            target = self._unwrap_redirect(anchor["href"])
            if target:
                urls.append(target)
            if len(urls) >= limit:
                break
        return urls

    @staticmethod
    def _unwrap_redirect(href: str) -> Optional[str]:
        if href.startswith("//"):
            href = "https:" + href
        parsed = urlparse(href)
        if parsed.netloc != "duckduckgo.com" or not parsed.path.startswith("/l/"):
            return href  # not wrapped; already a direct link
        target = parse_qs(parsed.query).get("uddg")
        return target[0] if target else None
