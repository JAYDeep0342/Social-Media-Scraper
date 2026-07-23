from app.metrics.collector import MetricsCollector
from app.metrics.cpu import get_process_cpu_percent
from app.metrics.ram import get_process_ram_mb
from app.metrics.timer import Stopwatch


def test_stopwatch_elapsed_is_non_negative() -> None:
    sw = Stopwatch()
    assert sw.elapsed_seconds() >= 0


def test_cpu_and_ram_helpers_return_numbers() -> None:
    assert isinstance(get_process_cpu_percent(), float)
    assert get_process_ram_mb() > 0


def test_metrics_collector_snapshot_has_expected_fields() -> None:
    collector = MetricsCollector()
    snapshot = collector.snapshot()
    assert snapshot.elapsed_seconds >= 0
    assert snapshot.ram_mb > 0
