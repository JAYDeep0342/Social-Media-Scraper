"""Async retry decorator with exponential backoff + jitter."""

import asyncio
import functools
import logging
import random
from typing import Any, Callable, Tuple, Type, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    """Retry an async callable on the given exception types with exponential
    backoff (capped at `max_delay`) plus random jitter."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.warning("%s failed after %d attempts: %s", func.__qualname__, attempt, exc)
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay) + random.uniform(0, base_delay)
                    logger.debug(
                        "%s attempt %d/%d failed: %s. Retrying in %.2fs",
                        func.__qualname__,
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)

        return wrapper  # type: ignore[return-value]

    return decorator
