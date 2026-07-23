"""Outcome metrics for a single Google Maps discovery run: discovery time,
cards collected, throughput, scroll count, and duplicate count.

Distinct from app.network.network_metrics (HTTP layer) and app.metrics
(process CPU/RAM) — this describes one discovery pipeline execution.
"""

from dataclasses import dataclass


@dataclass
class DiscoveryMetrics:
    discovery_time_seconds: float
    cards_collected: int
    cards_per_second: float
    scroll_count: int
    duplicate_count: int
