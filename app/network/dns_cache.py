"""Reusable DNS resolution cache. Wraps asyncio's resolver with a TTL cache
(reusing app.cache.MemoryCache) so repeated lookups of the same host skip
redundant DNS round-trips.

Not yet wired into the HTTP client's transport (that requires a custom
httpx Transport) — this is the standalone abstraction that a future
transport integration would sit on top of.
"""

import asyncio
import socket
from typing import List, Optional

from app.cache.memory_cache import MemoryCache
from app.config.settings import get_settings
from app.exceptions.network import DNSFailure


class DNSCache:
    def __init__(self, *, ttl_seconds: Optional[float] = None) -> None:
        settings = get_settings()
        self._cache = MemoryCache(default_ttl_seconds=ttl_seconds or settings.DNS_CACHE_TTL_SECONDS)

    async def resolve(self, hostname: str, port: int = 443) -> List[str]:
        cache_key = f"{hostname}:{port}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        loop = asyncio.get_running_loop()
        try:
            addrinfo = await loop.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        except (socket.gaierror, UnicodeError) as exc:
            # gaierror: the OS resolver rejected/couldn't resolve the name.
            # UnicodeError: malformed hostnames (e.g. an over-length label)
            # fail during IDNA encoding before any resolver call is made.
            raise DNSFailure(
                f"DNS resolution failed for '{hostname}'", details={"hostname": hostname}
            ) from exc

        addresses = sorted({info[4][0] for info in addrinfo})
        await self._cache.set(cache_key, addresses)
        return addresses

    async def clear(self) -> None:
        await self._cache.clear()
