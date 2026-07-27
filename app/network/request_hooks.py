"""Request-side event hooks for the shared HTTP client: a pre-request timing
stamp, User-Agent rotation, and structured logging. Wired into httpx via
`event_hooks={"request": [...]}`.
"""

import time

import httpx

from app.core.logging import get_logger
from app.network.user_agent import UserAgentManager

logger = get_logger(__name__)

_user_agents = UserAgentManager()


async def stamp_start_time(request: httpx.Request) -> None:
    request.extensions["start_time"] = time.perf_counter()


async def rotate_user_agent(request: httpx.Request) -> None:
    """Every outbound request otherwise carries httpx's own default
    User-Agent (`python-httpx/<version>`) since HTTPClientManager builds
    one shared client with no per-request header override -- an obvious
    automated-client signature that gets flagged/blocked by sites with
    basic bot detection (e.g. DuckDuckGo's html endpoint serving a JS
    challenge instead of results). Rotating a realistic browser
    User-Agent in here, per request, fixes that for every call through
    SessionManager without needing a header override at each call site."""
    request.headers["User-Agent"] = _user_agents.next()


async def log_outgoing_request(request: httpx.Request) -> None:
    logger.debug("-> %s %s", request.method, request.url)


DEFAULT_REQUEST_HOOKS = [stamp_start_time, rotate_user_agent, log_outgoing_request]
