"""In-memory caching layer. A Redis-backed cache can be added later behind
the same get/set/delete/clear shape."""

from app.cache.memory_cache import MemoryCache

__all__ = ["MemoryCache"]
