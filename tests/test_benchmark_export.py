import csv

from app.benchmark.benchmark import BenchmarkTimer


def test_benchmark_timer_export_csv_writes_header_and_row(tmp_path) -> None:
    csv_path = tmp_path / "benchmarks.csv"

    with BenchmarkTimer("demo_run") as bt:
        bt.record_success()

    bt.export_csv(csv_path)

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert rows[0]["name"] == "demo_run"
    assert rows[0]["success_count"] == "1"


def test_benchmark_timer_export_appends_across_runs(tmp_path) -> None:
    csv_path = tmp_path / "benchmarks.csv"

    with BenchmarkTimer("run_1") as bt1:
        bt1.record_success()
    bt1.export_csv(csv_path)

    with BenchmarkTimer("run_2") as bt2:
        bt2.record_failure()
    bt2.export_csv(csv_path)

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert [row["name"] for row in rows] == ["run_1", "run_2"]
