"""Lightweight in-memory TTL cache. No Redis, no persistence — process-local
only. Serves as the default cache until a distributed backend is needed.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

from app.config.constants import CACHE_TTL


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class MemoryCache:
    """A simple async-safe, per-key TTL cache backed by a dict."""

    def __init__(self, default_ttl_seconds: float = CACHE_TTL) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.monotonic():
                del self._store[key]
                return None
            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        ttl = self._default_ttl if ttl_seconds is None else ttl_seconds
        async with self._lock:
            self._store[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def size(self) -> int:
        async with self._lock:
            return len(self._store)
