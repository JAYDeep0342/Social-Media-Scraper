"""Caches enrichment outcomes so a business already processed (whether a
website was found or confirmed absent) is never re-enriched. Built on the
existing in-memory TTL cache (Phase 1.1) — no new caching mechanism.

MemoryCache.get() returns None for both "never cached" and "cached as
None," which would be ambiguous here (a business confirmed to have no
website must still count as a cache hit). `_CachedEnrichment` — a truthy
wrapper object — resolves that ambiguity.
"""

from dataclasses import dataclass
from typing import Optional

from app.cache.memory_cache import MemoryCache
from app.discovery.google_maps.dedup import extract_place_id


@dataclass
class CachedEnrichment:
    website: Optional[str]


class EnrichmentCache:
    def __init__(self, *, ttl_seconds: Optional[float] = None) -> None:
        self._cache = MemoryCache() if ttl_seconds is None else MemoryCache(default_ttl_seconds=ttl_seconds)

    @staticmethod
    def _key(maps_url: str) -> str:
        return extract_place_id(maps_url) or maps_url

    async def get(self, maps_url: str) -> Optional[CachedEnrichment]:
        return await self._cache.get(self._key(maps_url))

    async def set(self, maps_url: str, website: Optional[str]) -> None:
        await self._cache.set(self._key(maps_url), CachedEnrichment(website=website))

    async def has(self, maps_url: str) -> bool:
        return await self.get(maps_url) is not None
