"""Provider interface: the contract every future search/discovery provider
(Google, Bing, DuckDuckGo, ...) must implement. No network or search logic
lives here."""

from abc import ABC, abstractmethod
from typing import Any


class SearchProvider(ABC):
    """Contract for a source that can discover candidate leads for a
    keyword/location pair. Subclasses implement `discover`."""

    name: str = "unnamed_provider"

    @abstractmethod
    async def discover(self, keyword: str, location: str, limit: int) -> list[Any]:
        raise NotImplementedError
