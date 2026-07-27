"""Extracts business name, website, and Google Maps URL from each result
card currently rendered in the results feed. Extracts ONLY these three
fields — no phone, rating, or address.

Deliberately list-only: this never opens a card's detail panel. Verified
against live Google Maps, the results list does not expose a website link
for most cards — website enrichment (opening each place's detail panel) is
a separate, heavier operation left to a future phase. When a website link
genuinely isn't present on the card, `website` is correctly left as None.

All cards are read in a single `page.evaluate()` round trip rather than
N sequential Playwright locator calls per card — the DOM read itself still
costs O(cards), but that cost runs inside the page's own JS engine instead
of paying the Playwright IPC round-trip latency once per field per card.
The extracted field semantics are unchanged: same selectors, same
aria-label-then-class-name fallback for the name, same "website only if
the card itself exposes a link" rule.

A single bad card (unexpected/missing markup, or a normalization failure)
is logged and skipped rather than aborting the whole batch.
"""

from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from app.core.logging import get_logger
from app.discovery.google_maps import selectors
from app.models.domain import BusinessLead, SocialLead
from app.normalizers.business_name_normalizer import normalize_business_name
from app.normalizers.url_normalizer import normalize_business_url

logger = get_logger(__name__)

# Runs once per extract_all() call, reading every currently-rendered card's
# fields in-page. Mirrors the previous per-card Playwright-locator logic
# exactly: link href for the Maps URL, aria-label falling back to the
# card's name element for the business name, and a best-effort website
# link that's simply absent (null) when the card doesn't expose one.
_EXTRACT_CARDS_JS = """
([containerSel, linkSel, nameSel, websiteSel]) => {
    const containers = Array.from(document.querySelectorAll(containerSel));
    return containers.map(container => {
        const link = container.querySelector(linkSel);
        if (!link) return null;
        const mapsUrl = link.getAttribute('href');
        if (!mapsUrl) return null;

        let rawName = link.getAttribute('aria-label');
        if (!rawName) {
            const nameEl = container.querySelector(nameSel);
            rawName = nameEl ? nameEl.textContent : null;
        }
        if (!rawName) return null;

        const websiteEl = container.querySelector(websiteSel);
        const website = websiteEl ? websiteEl.getAttribute('href') : null;

        return { mapsUrl, rawName, website };
    });
}
"""


class CardExtractor:
    def __init__(self, page: Page) -> None:
        self._page = page

    async def extract_all(self, *, source_keyword: str, source_location: str) -> List[BusinessLead]:
        raw_cards = await self._page.evaluate(
            _EXTRACT_CARDS_JS,
            [
                selectors.RESULT_CARD_CONTAINER,
                selectors.RESULT_CARD_LINK_RELATIVE,
                selectors.RESULT_CARD_NAME,
                selectors.RESULT_CARD_WEBSITE_LINK,
            ],
        )

        leads: List[BusinessLead] = []
        for raw in raw_cards:
            if raw is None:
                continue
            lead = self._build_lead(raw, source_keyword=source_keyword, source_location=source_location)
            if lead is not None:
                leads.append(lead)
        return leads

    def _build_lead(
        self, raw: Dict[str, Any], *, source_keyword: str, source_location: str
    ) -> Optional[BusinessLead]:
        try:
            maps_url = raw.get("mapsUrl")
            raw_name = raw.get("rawName")
            if not maps_url or not raw_name:
                return None
            website = raw.get("website")

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
