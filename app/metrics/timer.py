"""Reusable wall-clock stopwatch for metrics collection.

Distinct from `app.utils.timer.Timer` (a single with-block stopwatch): this
one can be polled repeatedly for an elapsed reading without ending the
measurement, which `MetricsCollector` needs.
"""

import time


class Stopwatch:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_seconds(self) -> float:
        return round(time.perf_counter() - self._start, 4)

    def reset(self) -> None:
        self._start = time.perf_counter()
