import pytest

from app.enrichment.google_maps.metrics import EnrichmentMetrics


@pytest.mark.asyncio
async def test_initial_snapshot_is_zeroed() -> None:
    metrics = EnrichmentMetrics()
    snapshot = await metrics.snapshot()

    assert snapshot.total_enriched == 0
    assert snapshot.missing_websites == 0
    assert snapshot.success_rate == 0.0
    assert snapshot.average_enrichment_seconds == 0.0


@pytest.mark.asyncio
async def test_success_and_failure_counts_and_rate() -> None:
    metrics = EnrichmentMetrics()

    start = await metrics.start_one()
    await metrics.finish_one(start, success=True)

    start = await metrics.start_one()
    await metrics.finish_one(start, success=True)

    start = await metrics.start_one()
    await metrics.finish_one(start, success=False)

    snapshot = await metrics.snapshot()
    assert snapshot.total_enriched == 3
    assert snapshot.missing_websites == 1
    assert snapshot.success_rate == round(2 / 3 * 100, 2)


@pytest.mark.asyncio
async def test_average_enrichment_time_is_computed() -> None:
    metrics = EnrichmentMetrics()
    start = await metrics.start_one()
    await metrics.finish_one(start, success=True)

    snapshot = await metrics.snapshot()
    assert snapshot.average_enrichment_seconds >= 0


@pytest.mark.asyncio
async def test_reset_zeroes_everything() -> None:
    metrics = EnrichmentMetrics()
    start = await metrics.start_one()
    await metrics.finish_one(start, success=False)

    await metrics.reset()

    snapshot = await metrics.snapshot()
    assert snapshot.total_enriched == 0
    assert snapshot.missing_websites == 0
