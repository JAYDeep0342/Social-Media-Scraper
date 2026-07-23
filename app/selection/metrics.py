"""Tracks selection engine outcomes across a batch: total candidates seen,
duplicates merged away, candidates rejected (unusable), and how many final
URLs were selected.

Synchronous, unlike the metrics classes in Phases 2-5 — this whole engine
is pure in-memory computation with no I/O to synchronize concurrent
access around.
"""

from dataclasses import dataclass


@dataclass
class SelectionMetricsSnapshot:
    candidates: int
    duplicates: int
    rejected: int
    selected: int


class SelectionMetrics:
    def __init__(self) -> None:
        self._candidates = 0
        self._duplicates = 0
        self._rejected = 0
        self._selected = 0

    def record_candidates(self, count: int) -> None:
        self._candidates += count

    def record_duplicates(self, count: int) -> None:
        self._duplicates += count

    def record_rejected(self, count: int) -> None:
        self._rejected += count

    def record_selected(self, count: int) -> None:
        self._selected += count

    def snapshot(self) -> SelectionMetricsSnapshot:
        return SelectionMetricsSnapshot(
            candidates=self._candidates,
            duplicates=self._duplicates,
            rejected=self._rejected,
            selected=self._selected,
        )

    def reset(self) -> None:
        self._candidates = 0
        self._duplicates = 0
        self._rejected = 0
        self._selected = 0
