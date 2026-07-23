import pytest

from app.network.network_metrics import NetworkMetrics


@pytest.mark.asyncio
async def test_records_success_and_failure_counts() -> None:
    metrics = NetworkMetrics()

    start = await metrics.record_request_start()
    await metrics.record_request_end(start, success=True)

    start = await metrics.record_request_start()
    await metrics.record_request_end(start, success=False)

    snapshot = await metrics.snapshot()
    assert snapshot.total_requests == 2
    assert snapshot.successful_requests == 1
    assert snapshot.failed_requests == 1
    assert snapshot.open_connections == 0


@pytest.mark.asyncio
async def test_average_latency_is_computed() -> None:
    metrics = NetworkMetrics()
    start = await metrics.record_request_start()
    await metrics.record_request_end(start, success=True)

    snapshot = await metrics.snapshot()
    assert snapshot.average_latency_ms >= 0


@pytest.mark.asyncio
async def test_retry_count_increments() -> None:
    metrics = NetworkMetrics()
    await metrics.record_retry()
    await metrics.record_retry()

    snapshot = await metrics.snapshot()
    assert snapshot.retry_count == 2


@pytest.mark.asyncio
async def test_open_connections_tracked_during_in_flight_request() -> None:
    metrics = NetworkMetrics()
    start = await metrics.record_request_start()

    mid_snapshot = await metrics.snapshot()
    assert mid_snapshot.open_connections == 1

    await metrics.record_request_end(start, success=True)
    end_snapshot = await metrics.snapshot()
    assert end_snapshot.open_connections == 0


@pytest.mark.asyncio
async def test_reset_zeroes_all_counters() -> None:
    metrics = NetworkMetrics()
    start = await metrics.record_request_start()
    await metrics.record_request_end(start, success=True)
    await metrics.record_retry()

    await metrics.reset()

    snapshot = await metrics.snapshot()
    assert snapshot.total_requests == 0
    assert snapshot.retry_count == 0
    assert snapshot.average_latency_ms == 0
