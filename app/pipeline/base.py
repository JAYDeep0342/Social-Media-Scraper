"""Generic, reusable pipeline base classes.

A `Pipeline` runs a sequence of `PipelineStage` instances over a batch of
items, with concurrency bounded the same way the rest of the app bounds
concurrency (`app.utils.async_helper.gather_with_concurrency`). Neither class
carries any domain knowledge — future modules (discovery, extraction,
enrichment, etc.) subclass `PipelineStage` and compose them into a `Pipeline`.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Sequence, TypeVar

from app.config.settings import get_settings
from app.utils.async_helper import gather_with_concurrency

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class PipelineStage(ABC, Generic[InputT, OutputT]):
    """A single unit of work in a pipeline. Subclasses implement `process`."""

    name: str = "unnamed_stage"

    @abstractmethod
    async def process(self, item: InputT) -> OutputT:
        raise NotImplementedError


class Pipeline(Generic[InputT, OutputT]):
    """Runs an ordered sequence of stages over one item or a batch of items."""

    def __init__(self, stages: Sequence[PipelineStage], *, concurrency: Optional[int] = None) -> None:
        self.stages = list(stages)
        self.concurrency = concurrency or get_settings().MAX_CONCURRENCY

    async def run_one(self, item: InputT) -> OutputT:
        result: Any = item
        for stage in self.stages:
            result = await stage.process(result)
        return result

    async def run_many(self, items: Sequence[InputT]) -> list[OutputT]:
        return await gather_with_concurrency(self.concurrency, *(self.run_one(item) for item in items))
