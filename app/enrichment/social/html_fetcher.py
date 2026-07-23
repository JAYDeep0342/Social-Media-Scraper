"""Downloads a business's homepage HTML via the existing Phase 2
networking layer (SessionManager) — plain HTTP only, no browser. A failed
fetch is a normal, expected outcome (dead site, timeout, non-2xx) and
returns None rather than raising, since not every business's website
needs to succeed for the batch to proceed.
"""

from typing import Optional

from app.core.logging import get_logger
from app.network.session_manager import SessionManager

logger = get_logger(__name__)


class WebsiteHTMLFetcher:
    def __init__(self, session_manager: Optional[SessionManager] = None) -> None:
        self._session_manager = session_manager

    def _get_session_manager(self) -> SessionManager:
        return self._session_manager or SessionManager.get_instance()

    async def fetch(self, url: str) -> Optional[str]:
        try:
            response = await self._get_session_manager().request("GET", url)
        except Exception as exc:
            logger.warning("Failed to fetch homepage HTML for %s: %s", url, exc)
            return None

        if response.status_code >= 400:
            logger.warning("Homepage fetch for %s returned status %s", url, response.status_code)
            return None

        return response.text
