"""Request-side event hooks for the shared HTTP client: a pre-request timing
stamp and structured logging. Wired into httpx via
`event_hooks={"request": [...]}`.
"""

import time

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


async def stamp_start_time(request: httpx.Request) -> None:
    request.extensions["start_time"] = time.perf_counter()


async def log_outgoing_request(request: httpx.Request) -> None:
    logger.debug("-> %s %s", request.method, request.url)


DEFAULT_REQUEST_HOOKS = [stamp_start_time, log_outgoing_request]
