"""Bing search provider — interface stub only. Not implemented yet."""

from typing import Any

from app.providers.base import SearchProvider


class BingSearchProvider(SearchProvider):
    name = "bing"

    async def discover(self, keyword: str, location: str, limit: int) -> list[Any]:
        raise NotImplementedError("BingSearchProvider is not implemented yet.")
