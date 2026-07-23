"""Generic async helpers for bounded concurrency and timeouts."""

import asyncio
from typing import Awaitable, List, TypeVar

from app.exceptions.errors import ScraperTimeoutError

T = TypeVar("T")


async def gather_with_concurrency(limit: int, *tasks: Awaitable[T]) -> List[T]:
    """Run awaitables concurrently, bounded by a semaphore of size `limit`."""
    semaphore = asyncio.Semaphore(limit)

    async def _run(task: Awaitable[T]) -> T:
        async with semaphore:
            return await task

    return await asyncio.gather(*(_run(task) for task in tasks))


async def run_with_timeout(coro: Awaitable[T], timeout_seconds: float, *, label: str = "operation") -> T:
    """Await a coroutine with a timeout, raising our domain ScraperTimeoutError on expiry."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise ScraperTimeoutError(f"{label} timed out after {timeout_seconds}s") from exc
