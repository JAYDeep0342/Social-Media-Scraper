import asyncio

import pytest

from app.cache.memory_cache import MemoryCache


@pytest.mark.asyncio
async def test_set_and_get_roundtrip() -> None:
    cache = MemoryCache()
    await cache.set("k", "v")
    assert await cache.get("k") == "v"


@pytest.mark.asyncio
async def test_missing_key_returns_none() -> None:
    cache = MemoryCache()
    assert await cache.get("missing") is None


@pytest.mark.asyncio
async def test_entry_expires_after_ttl() -> None:
    cache = MemoryCache()
    await cache.set("k", "v", ttl_seconds=0.05)
    assert await cache.get("k") == "v"
    await asyncio.sleep(0.1)
    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_delete_and_clear() -> None:
    cache = MemoryCache()
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.delete("a")
    assert await cache.get("a") is None
    assert await cache.size() == 1
    await cache.clear()
    assert await cache.size() == 0
