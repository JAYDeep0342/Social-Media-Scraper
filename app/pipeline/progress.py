"""Tracks orchestrator-level progress across the whole pipeline run:
current stage, running completed/failed business counts (accumulated as
each stage finishes), and total elapsed time.

Distinct from app.discovery.google_maps.progress_tracker.ProgressTracker
(which tracks collected/remaining/cards-per-sec during Discovery's own
scroll loop specifically) — this one spans the entire orchestrated
pipeline across all four stages.
"""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineProgressSnapshot:
    current_stage: Optional[str]
    completed_businesses: int
    failed_businesses: int
    elapsed_seconds: float


class PipelineProgressTracker:
    def __init__(self) -> None:
        self._start = time.perf_counter()
        self._current_stage: Optional[str] = None
        self._completed = 0
        self._failed = 0

    def start_stage(self, name: str) -> None:
        self._current_stage = name

    def finish_stage(self, name: str, *, completed: int, failed: int) -> None:
        self._current_stage = name
        self._completed += completed
        self._failed += failed

    def snapshot(self) -> PipelineProgressSnapshot:
        return PipelineProgressSnapshot(
            current_stage=self._current_stage,
            completed_businesses=self._completed,
            failed_businesses=self._failed,
            elapsed_seconds=round(time.perf_counter() - self._start, 3),
        )
