"""Extracts business name, website, and Google Maps URL from each result
card currently rendered in the results feed. Extracts ONLY these three
fields — no phone, rating, or address.

Deliberately list-only: this never opens a card's detail panel. Verified
against live Google Maps, the results list does not expose a website link
for most cards — website enrichment (opening each place's detail panel) is
a separate, heavier operation left to a future phase. When a website link
genuinely isn't present on the card, `website` is correctly left as None.

A single bad card (unexpected/missing markup) is logged and skipped rather
than aborting the whole batch.
"""

from typing import List, Optional

from playwright.async_api import Locator, Page

from app.core.logging import get_logger
from app.discovery.google_maps import selectors
from app.models.domain import BusinessLead, SocialLead
from app.normalizers.business_name_normalizer import normalize_business_name
from app.normalizers.url_normalizer import normalize_business_url

logger = get_logger(__name__)


class CardExtractor:
    def __init__(self, page: Page) -> None:
        self._page = page

    async def extract_all(self, *, source_keyword: str, source_location: str) -> List[BusinessLead]:
        containers = self._page.locator(selectors.RESULT_CARD_CONTAINER)
        count = await containers.count()

        leads: List[BusinessLead] = []
        for i in range(count):
            lead = await self._extract_one(
                containers.nth(i), source_keyword=source_keyword, source_location=source_location
            )
            if lead is not None:
                leads.append(lead)
        return leads

    async def _extract_one(
        self, container: Locator, *, source_keyword: str, source_location: str
    ) -> Optional[BusinessLead]:
        try:
            link = container.locator(selectors.RESULT_CARD_LINK_RELATIVE)
            if await link.count() == 0:
                return None
            maps_url = await link.first.get_attribute("href")
            if not maps_url:
                return None

            raw_name = await link.first.get_attribute("aria-label")
            if not raw_name:
                name_locator = container.locator(selectors.RESULT_CARD_NAME)
                raw_name = await name_locator.first.text_content() if await name_locator.count() > 0 else None
            if not raw_name:
                return None

            website = await self._extract_website(container)

            return BusinessLead(
                business_name=normalize_business_name(raw_name),
                website=normalize_business_url(website) if website else None,
                social=SocialLead(google_maps_url=maps_url),
                source_keyword=source_keyword,
                source_location=source_location,
            )
        except Exception:
            logger.warning("Skipping a result card that failed to extract cleanly", exc_info=True)
            return None

    async def _extract_website(self, container: Locator) -> Optional[str]:
        """Best-effort: only returns a value when the list card itself
        exposes a website link. Never opens the detail panel."""
        website_link = container.locator(selectors.RESULT_CARD_WEBSITE_LINK)
        if await website_link.count() == 0:
            return None
        return await website_link.first.get_attribute("href")
