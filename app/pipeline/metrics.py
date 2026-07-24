"""Aggregate pipeline-level metrics: per-stage execution time, overall
execution time, throughput (businesses/sec), and success rate.
"""

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PipelineMetricsSnapshot:
    stage_times: Dict[str, float]
    overall_seconds: float
    throughput_per_second: float
    success_rate: float


class PipelineMetrics:
    def __init__(self) -> None:
        self._start = time.perf_counter()
        self._stage_times: Dict[str, float] = {}

    def record_stage_time(self, stage: str, seconds: float) -> None:
        self._stage_times[stage] = self._stage_times.get(stage, 0.0) + seconds

    def snapshot(self, *, total_businesses: int, successful_businesses: int) -> PipelineMetricsSnapshot:
        overall = time.perf_counter() - self._start
        throughput = (total_businesses / overall) if overall > 0 else 0.0
        success_rate = (successful_businesses / total_businesses * 100) if total_businesses else 0.0
        return PipelineMetricsSnapshot(
            stage_times={k: round(v, 4) for k, v in self._stage_times.items()},
            overall_seconds=round(overall, 4),
            throughput_per_second=round(throughput, 2),
            success_rate=round(success_rate, 2),
        )
