from app.pipeline.progress import PipelineProgressTracker


def test_initial_snapshot_has_no_stage_and_zero_counts() -> None:
    tracker = PipelineProgressTracker()
    snapshot = tracker.snapshot()
    assert snapshot.current_stage is None
    assert snapshot.completed_businesses == 0
    assert snapshot.failed_businesses == 0
    assert snapshot.elapsed_seconds >= 0


def test_start_stage_updates_current_stage_without_changing_counts() -> None:
    tracker = PipelineProgressTracker()
    tracker.start_stage("maps_discovery")
    snapshot = tracker.snapshot()
    assert snapshot.current_stage == "maps_discovery"
    assert snapshot.completed_businesses == 0


def test_finish_stage_accumulates_across_multiple_stages() -> None:
    tracker = PipelineProgressTracker()
    tracker.finish_stage("maps_discovery", completed=10, failed=0)
    tracker.finish_stage("website_enrichment", completed=7, failed=3)

    snapshot = tracker.snapshot()
    assert snapshot.current_stage == "website_enrichment"
    assert snapshot.completed_businesses == 17
    assert snapshot.failed_businesses == 3
