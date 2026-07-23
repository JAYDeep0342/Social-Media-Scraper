"""Google Maps detail-panel DOM selectors, centralized like
app.discovery.google_maps.selectors — same caveat: no public API, so these
are subject to drift as Google's markup changes.

Verified against a live detail panel on 2026-07-23 (opened by navigating
directly to a captured place URL — see detail_navigator.py's docstring for
why the URL must be the full, unmodified one from discovery):

- `DETAIL_PANEL_ROOT` (`div[role="main"]`): the panel's root container,
  aria-labelled with the business name. Present for every business
  regardless of whether it has a website, so this is the "panel loaded"
  wait condition — NOT the website link, which is frequently absent.
- `WEBSITE_LINK` (`a[data-item-id="authority"]`): Google's internal
  data-item-id for the official website button. Verified: its `href` is
  the real external URL (e.g. a business's storefront site), not a Google
  redirect link.
"""

DETAIL_PANEL_ROOT = 'div[role="main"]'
WEBSITE_LINK = 'a[data-item-id="authority"]'
