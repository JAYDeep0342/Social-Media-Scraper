import pytest

from app.exceptions.network import DNSFailure
from app.network.dns_cache import DNSCache


@pytest.mark.asyncio
async def test_resolve_localhost_returns_addresses() -> None:
    cache = DNSCache()
    addresses = await cache.resolve("localhost", port=80)
    assert len(addresses) > 0


@pytest.mark.asyncio
async def test_resolve_caches_result() -> None:
    cache = DNSCache()
    first = await cache.resolve("localhost", port=80)
    second = await cache.resolve("localhost", port=80)
    assert first == second


@pytest.mark.asyncio
async def test_resolve_invalid_hostname_raises_dns_failure() -> None:
    cache = DNSCache()
    # A single DNS label over 63 chars is invalid per RFC 1035 and is
    # rejected by getaddrinfo locally, with no dependency on network
    # availability or DNS provider behavior.
    bogus_hostname = "a" * 300 + ".com"

    with pytest.raises(DNSFailure):
        await cache.resolve(bogus_hostname)


@pytest.mark.asyncio
async def test_clear_empties_the_cache() -> None:
    cache = DNSCache()
    await cache.resolve("localhost", port=80)
    await cache.clear()
    assert await cache._cache.size() == 0
