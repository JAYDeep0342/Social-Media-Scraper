from app.selection.metrics import SelectionMetrics


def test_initial_snapshot_is_zeroed() -> None:
    metrics = SelectionMetrics()
    snapshot = metrics.snapshot()
    assert snapshot.candidates == 0
    assert snapshot.duplicates == 0
    assert snapshot.rejected == 0
    assert snapshot.selected == 0


def test_records_all_counters() -> None:
    metrics = SelectionMetrics()
    metrics.record_candidates(5)
    metrics.record_duplicates(2)
    metrics.record_rejected(1)
    metrics.record_selected(2)

    snapshot = metrics.snapshot()
    assert snapshot.candidates == 5
    assert snapshot.duplicates == 2
    assert snapshot.rejected == 1
    assert snapshot.selected == 2


def test_counters_accumulate_across_calls() -> None:
    metrics = SelectionMetrics()
    metrics.record_candidates(3)
    metrics.record_candidates(4)
    assert metrics.snapshot().candidates == 7


def test_reset_zeroes_everything() -> None:
    metrics = SelectionMetrics()
    metrics.record_candidates(5)
    metrics.record_selected(2)
    metrics.reset()
    snapshot = metrics.snapshot()
    assert snapshot.candidates == 0
    assert snapshot.selected == 0
