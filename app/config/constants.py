
"""Static, non-configurable constants. Anything an operator should be able to
change at deploy time belongs in settings.py instead."""

APP_TITLE = "Social Scraper API"
APP_DESCRIPTION = (
    "High-performance async backend for aggregating public business and "
    "social profile leads."
)
API_V1_PREFIX = "/api/v1"

DEFAULT_LEAD_LIMIT = 20
MAX_LEADS = 500

# --- Concurrency / worker ceilings ---

MAX_CONCURRENCY = 20
MAX_HTTP_CONNECTIONS = 100
MAX_SEARCH_WORKERS = 10

# --- Timeouts (seconds) ---
DEFAULT_TIMEOUT = 10.0
SOCIAL_DISCOVERY_TIMEOUT = 8.0
WEBSITE_TIMEOUT = 10.0
SEARCH_TIMEOUT = 12.0

# --- Retries ---
MAX_RETRIES = 3

# --- Cache ---
CACHE_TTL = 300  # seconds

# --- Networking: HTTP client ---
CONNECT_TIMEOUT_SECONDS = 5.0
CONNECTION_POOL_SIZE_PER_HOST = 20
HTTP2_ENABLED = True

# --- Networking: retry engine ---
RETRY_BACKOFF_BASE = 0.5
RETRY_MAX_DELAY_SECONDS = 8.0
RETRY_JITTER_SECONDS = 0.5

# --- Networking: circuit breaker ---
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS = 30.0
CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS = 1

# --- Networking: rate limiter (token bucket) ---
RATE_LIMIT_REQUESTS_PER_SECOND = 10.0
RATE_LIMIT_BURST = 20

# --- Networking: DNS cache ---
DNS_CACHE_TTL_SECONDS = 300.0

# --- Networking: compression (configuration only; httpx handles the actual
# decoding). "br" is only advertised if a brotli decoder is installed. ---
BASE_ACCEPTED_ENCODINGS = ("gzip", "deflate")

# --- Google Maps discovery: browser ---
GOOGLE_MAPS_BASE_URL = "https://www.google.com/maps"
BROWSER_HEADLESS = True
BROWSER_NAVIGATION_TIMEOUT_SECONDS = 30.0
BROWSER_POOL_SIZE = 12
VIEWPORT_WIDTH = 1366
VIEWPORT_HEIGHT = 768

# --- Google Maps discovery: scrolling ---
SCROLL_PAUSE_SECONDS = 1.2
SCROLL_MAX_ATTEMPTS_WITHOUT_PROGRESS = 4
SCROLL_MAX_TOTAL_ATTEMPTS = 60
# How often to re-check the card count during a scroll's pause window,
# so a fast-loading scroll doesn't sit out a slower scroll's full backoff.
SCROLL_POLL_INTERVAL_SECONDS = 0.25

# --- Google Maps website enrichment ---
ENRICHMENT_WORKER_COUNT = 12

# --- URL confidence & dedup engine ---
CONFIDENCE_SCORE_HIGH = 100
CONFIDENCE_SCORE_MEDIUM = 70
CONFIDENCE_SCORE_LOW = 40
CONFIDENCE_SCORE_NONE = 0

# --- Social discovery --
# -
# DuckDuckGo's html-only endpoint requires no JS rendering, unlike
# Google/Bing's search UIs — the only search provider actually implemented
# in Phase 5 ("prefer HTTP requests... avoid Playwright unless necessary").
DUCKDUCKGO_HTML_ENDPOINT = "https://html.duckduckgo.com/html/"
SOCIAL_SEARCH_RESULT_LIMIT = 10
# Deliberately shorter than the general REQUEST_TIMEOUT_SECONDS: a slow or
# blocked search-engine fallback is a "no results" outcome either way, so
# there's nothing to gain from waiting the full default timeout (or all
# MAX_RETRIES attempts at that length) on a single business before moving
# on to the next one.
SOCIAL_SEARCH_TIMEOUT_SECONDS = 4.0
# How long BrowserWebsiteHTMLFetcher waits for a business's own homepage to
# navigate before giving up and moving to the DDG fallback. Verified live:
# with images/fonts/media/stylesheets blocked (see browser_html_fetcher.py),
# a working site loads well within a few seconds even under full worker
# concurrency, so a genuinely slow/unreachable site doesn't need the full
# 20s once given -- that just delays every other business queued behind it.
SOCIAL_BROWSER_FETCH_TIMEOUT_SECONDS = 15.0
SOCIAL_BROWSER_NETWORKIDLE_TIMEOUT_SECONDS = 4.0

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT_CONSOLE = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_FORMAT_FILE = "%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(lineno)d | %(message)s"
