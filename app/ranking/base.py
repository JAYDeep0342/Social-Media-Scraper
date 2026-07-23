"""Ranking package — architecture only, no scoring algorithm implemented yet."""

from abc import ABC, abstractmethod
from typing import Generic, Sequence, TypeVar

ItemT = TypeVar("ItemT")


class Ranker(ABC, Generic[ItemT]):
    """Contract for a future lead-ranking strategy. Subclasses implement `rank`."""

    name: str = "unnamed_ranker"

    @abstractmethod
    def rank(self, items: Sequence[ItemT]) -> list[ItemT]:
        raise NotImplementedError
