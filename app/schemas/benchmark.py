"""Schema describing the outcome of a benchmarked operation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BenchmarkResult(BaseModel):
    name: str
    execution_time_seconds: float
    cpu_percent: float
    ram_mb: float
    success_count: int = 0
    failure_count: int = 0
    started_at: datetime
    finished_at: datetime
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_count(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return round(self.success_count / self.total_count * 100, 2)
