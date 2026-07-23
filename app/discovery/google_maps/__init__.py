"""Google Maps discovery engine: browser automation over Google Maps search
results to collect business_name, website (when visible), and
google_maps_url. No phone/rating/address, no website content analysis, no
Instagram/Facebook/search-engine discovery — see the module docstrings in
this package for the exact boundaries.
"""

from app.discovery.google_maps.browser_manager import BrowserManager
from app.discovery.google_maps.browser_pool import BrowserContextPool
from app.discovery.google_maps.card_extractor import CardExtractor
from app.discovery.google_maps.dedup import deduplicate_leads, extract_place_id
from app.discovery.google_maps.maps_navigator import MapsNavigator
from app.discovery.google_maps.metrics import DiscoveryMetrics
from app.discovery.google_maps.pipeline import (
    DiscoveryContext,
    DiscoveryResult,
    build_discovery_pipeline,
    run_discovery,
)
from app.discovery.google_maps.progress_tracker import ProgressSnapshot, ProgressTracker
from app.discovery.google_maps.scroll_engine import ScrollEngine, ScrollResult

__all__ = [
    "BrowserManager",
    "BrowserContextPool",
    "MapsNavigator",
    "ScrollEngine",
    "ScrollResult",
    "CardExtractor",
    "deduplicate_leads",
    "extract_place_id",
    "ProgressTracker",
    "ProgressSnapshot",
    "DiscoveryMetrics",
    "DiscoveryContext",
    "DiscoveryResult",
    "build_discovery_pipeline",
    "run_discovery",
]
