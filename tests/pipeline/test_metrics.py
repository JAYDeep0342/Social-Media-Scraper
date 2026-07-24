from app.pipeline.metrics import PipelineMetrics


def test_snapshot_with_no_stages_recorded() -> None:
    metrics = PipelineMetrics()
    snapshot = metrics.snapshot(total_businesses=0, successful_businesses=0)
    assert snapshot.stage_times == {}
    assert snapshot.success_rate == 0.0


def test_records_stage_times() -> None:
    metrics = PipelineMetrics()
    metrics.record_stage_time("maps_discovery", 1.5)
    metrics.record_stage_time("website_enrichment", 0.5)

    snapshot = metrics.snapshot(total_businesses=10, successful_businesses=8)
    assert snapshot.stage_times["maps_discovery"] == 1.5
    assert snapshot.stage_times["website_enrichment"] == 0.5


def test_repeated_stage_time_recordings_accumulate() -> None:
    metrics = PipelineMetrics()
    metrics.record_stage_time("social_discovery", 0.3)
    metrics.record_stage_time("social_discovery", 0.2)

    snapshot = metrics.snapshot(total_businesses=1, successful_businesses=1)
    assert snapshot.stage_times["social_discovery"] == 0.5


def test_success_rate_computed_from_counts() -> None:
    metrics = PipelineMetrics()
    snapshot = metrics.snapshot(total_businesses=4, successful_businesses=3)
    assert snapshot.success_rate == 75.0


def test_throughput_is_non_negative() -> None:
    metrics = PipelineMetrics()
    snapshot = metrics.snapshot(total_businesses=10, successful_businesses=10)
    assert snapshot.throughput_per_second >= 0
