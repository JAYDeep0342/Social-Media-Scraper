"""Extracts ONLY the official website link from an already-open Google Maps
detail panel. No phone, rating, address, or website content is read —
just the href of the website button, or None if the business has none
listed.
"""

from typing import Optional

from playwright.async_api import Page

from app.enrichment.google_maps import selectors


class WebsiteExtractor:
    def __init__(self, page: Page) -> None:
        self._page = page

    async def extract(self) -> Optional[str]:
        link = self._page.locator(selectors.WEBSITE_LINK)
        if await link.count() == 0:
            return None
        return await link.first.get_attribute("href")
