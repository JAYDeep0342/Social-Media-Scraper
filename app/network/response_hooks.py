"""Response-side event hooks for the shared HTTP client: latency logging and
optional status validation. Wired into httpx via
`event_hooks={"response": [...]}`.

Request/response *counting* metrics (totals, success/failure, retries) are
tracked by SessionManager, which has clear before/after boundaries around
the whole retry+circuit-breaker call; these hooks handle the per-request
observability (timing + logging) that only the raw HTTP layer can see.
"""

import time

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


async def log_response(response: httpx.Response) -> None:
    start_time = response.request.extensions.get("start_time")
    if start_time is None:
        logger.debug("<- %s %s", response.status_code, response.request.url)
        return
    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.debug("<- %s %s (%.2fms)", response.status_code, response.request.url, duration_ms)


async def validate_status_hook(response: httpx.Response) -> None:
    """Opt-in hook: raises httpx.HTTPStatusError on 4xx/5xx. Not included in
    DEFAULT_RESPONSE_HOOKS by default since whether a non-2xx status should
    raise is a per-call decision, not a blanket rule for every request."""
    response.raise_for_status()


DEFAULT_RESPONSE_HOOKS = [log_response]
