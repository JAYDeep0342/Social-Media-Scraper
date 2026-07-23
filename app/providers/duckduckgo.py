"""DuckDuckGo search provider — interface stub only. Not implemented yet."""

from typing import Any

from app.providers.base import SearchProvider


class DuckDuckGoSearchProvider(SearchProvider):
    name = "duckduckgo"

    async def discover(self, keyword: str, location: str, limit: int) -> list[Any]:
        raise NotImplementedError("DuckDuckGoSearchProvider is not implemented yet.")
