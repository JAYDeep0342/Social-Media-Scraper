"""Lightweight stopwatch helpers, independent of the benchmark package
(which additionally tracks CPU/RAM/success counts)."""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class Timer:
    """Simple reusable stopwatch context manager."""

    def __init__(self) -> None:
        self.elapsed_seconds: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed_seconds = round(time.perf_counter() - self._start, 4)


def timeit(func: F) -> F:
    """Decorator that logs the execution time of a sync or async function."""
    logger = logging.getLogger(func.__module__)

    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                logger.debug("%s took %.4fs", func.__qualname__, time.perf_counter() - start)

        return async_wrapper  # type: ignore[return-value]

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            logger.debug("%s took %.4fs", func.__qualname__, time.perf_counter() - start)

    return sync_wrapper  # type: ignore[return-value]
