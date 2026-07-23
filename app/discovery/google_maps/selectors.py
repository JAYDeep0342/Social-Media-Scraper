"""Google Maps DOM selectors, centralized so they're a single point of
maintenance as Google's markup changes over time — Google Maps has no
public API for search results, so this UI-scraping approach is inherently
subject to selector drift.

These were verified against live Google Maps (www.google.com/maps) on
2026-07-23 for an English/US session. Notes on stability:

- `SEARCH_BOX_INPUT`: the input's `id` is dynamically generated per session
  (e.g. "ucc-1"), so `name="q"` is used instead — verified stable.
- `RESULTS_FEED` / `RESULT_CARD_LINK`: `div[role="feed"]` and the
  `/maps/place/` href pattern are structural/routing conventions, not
  obfuscated CSS classes, so they're expected to be relatively durable.
- `RESULT_CARD_CONTAINER` (`div.Nv2PK`): an obfuscated per-build CSS class.
  This is the least stable selector here and the most likely to need
  updating after a future Google Maps UI change.
- `RESULT_CARD_WEBSITE_LINK`: NOT observed in the verification session (the
  results list did not expose a website link for any card in that query) —
  kept as a best-effort selector per community-documented patterns, in case
  Google shows it for other business categories/locales/UI experiments.
  When it doesn't match, card_extractor correctly returns website=None.
- End-of-list detection: no textual "end of list" marker was observed after
  repeated scrolling; the reliable, verified signal is the result count
  plateauing across consecutive scrolls (see scroll_engine.py), which is
  why `END_OF_LIST_TEXT` is only a secondary, best-effort check.
"""

SEARCH_BOX_INPUT = 'input[name="q"]'

RESULTS_FEED = 'div[role="feed"]'
RESULT_CARD_LINK = 'div[role="feed"] a[href*="/maps/place/"]'  # absolute; used for counting
RESULT_CARD_LINK_RELATIVE = 'a[href*="/maps/place/"]'  # relative to a card container
RESULT_CARD_CONTAINER = 'div[role="feed"] div.Nv2PK'
RESULT_CARD_NAME = ".qBF1Pd"
RESULT_CARD_WEBSITE_LINK = 'a[data-value="Website"]'  # best-effort; often absent

END_OF_LIST_TEXT = "You've reached the end of the list"
