"""Google search provider — interface stub only. Not implemented yet."""

from typing import Any

from app.providers.base import SearchProvider


class GoogleSearchProvider(SearchProvider):
    name = "google"

    async def discover(self, keyword: str, location: str, limit: int) -> list[Any]:
        raise NotImplementedError("GoogleSearchProvider is not implemented yet.")
