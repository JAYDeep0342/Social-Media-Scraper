
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

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT_CONSOLE = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_FORMAT_FILE = "%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(lineno)d | %(message)s"
