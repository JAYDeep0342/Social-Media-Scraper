from pathlib import Path

from app.enrichment.social.confidence import Confidence
from app.selection.benchmarks import BENCHMARK_TIERS, run_benchmarks
from app.selection.candidate import make_candidate


def _business_candidates(i: int):
    return [
        make_candidate(platform="instagram", url=f"https://www.instagram.com/biz{i}", source="json_ld", confidence=Confidence.HIGH),
        make_candidate(platform="facebook", url=f"https://www.facebook.com/biz{i}", source="footer", confidence=Confidence.HIGH),
    ]


def test_run_benchmarks_produces_one_result_per_batch(tmp_path) -> None:
    batch_10 = [_business_candidates(i) for i in range(10)]
    batch_25 = [_business_candidates(i) for i in range(25)]
    csv_path = tmp_path / "selection_benchmarks.csv"

    results = run_benchmarks([batch_10, batch_25], csv_path=csv_path)

    assert [r.success_count for r in results] == [10, 25]
    assert csv_path.exists()


def test_default_tiers_include_1000() -> None:
    assert BENCHMARK_TIERS == (10, 25, 50, 100, 1000)
