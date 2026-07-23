import pytest

from app.pipeline.base import Pipeline, PipelineStage


class _AddOne(PipelineStage[int, int]):
    name = "add_one"

    async def process(self, item: int) -> int:
        return item + 1


class _Double(PipelineStage[int, int]):
    name = "double"

    async def process(self, item: int) -> int:
        return item * 2


@pytest.mark.asyncio
async def test_run_one_chains_stages_in_order() -> None:
    pipeline = Pipeline([_AddOne(), _Double()])
    assert await pipeline.run_one(1) == 4  # (1 + 1) * 2


@pytest.mark.asyncio
async def test_run_many_preserves_order() -> None:
    pipeline = Pipeline([_AddOne()], concurrency=2)
    assert await pipeline.run_many([1, 2, 3]) == [2, 3, 4]


def test_pipeline_stage_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        PipelineStage()  # type: ignore[abstract]
