import time

from app.discovery.google_maps.progress_tracker import ProgressTracker


def test_initial_snapshot_has_zero_collected_and_full_remaining() -> None:
    tracker = ProgressTracker(target_limit=50)
    snapshot = tracker.snapshot()

    assert snapshot.collected == 0
    assert snapshot.remaining == 50
    assert snapshot.elapsed_seconds >= 0


def test_update_reflects_in_snapshot() -> None:
    tracker = ProgressTracker(target_limit=50)
    tracker.update(20)
    snapshot = tracker.snapshot()

    assert snapshot.collected == 20
    assert snapshot.remaining == 30


def test_remaining_never_goes_negative_when_over_target() -> None:
    tracker = ProgressTracker(target_limit=10)
    tracker.update(15)
    snapshot = tracker.snapshot()

    assert snapshot.remaining == 0


def test_cards_per_second_is_computed() -> None:
    tracker = ProgressTracker(target_limit=100)
    time.sleep(0.05)
    tracker.update(10)
    snapshot = tracker.snapshot()

    assert snapshot.cards_per_second > 0
