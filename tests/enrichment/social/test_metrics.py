import pytest

from app.enrichment.social.metrics import SocialDiscoveryMetrics


@pytest.mark.asyncio
async def test_initial_snapshot_is_zeroed() -> None:
    metrics = SocialDiscoveryMetrics()
    snapshot = await metrics.snapshot()

    assert snapshot.total_processed == 0
    assert snapshot.html_fetch_success == 0
    assert snapshot.website_success == 0
    assert snapshot.search_fallback_used == 0
    assert snapshot.instagram_found == 0
    assert snapshot.facebook_found == 0
    assert snapshot.average_processing_seconds == 0.0


@pytest.mark.asyncio
async def test_tracks_all_counters() -> None:
    metrics = SocialDiscoveryMetrics()

    await metrics.record_html_fetch(True)
    await metrics.record_html_fetch(False)
    await metrics.record_website_success()
    await metrics.record_search_fallback_used()

    start = await metrics.start_one()
    await metrics.finish_one(start, instagram_found=True, facebook_found=False)

    start = await metrics.start_one()
    await metrics.finish_one(start, instagram_found=False, facebook_found=True)

    snapshot = await metrics.snapshot()
    assert snapshot.total_processed == 2
    assert snapshot.html_fetch_success == 1
    assert snapshot.website_success == 1
    assert snapshot.search_fallback_used == 1
    assert snapshot.instagram_found == 1
    assert snapshot.facebook_found == 1


@pytest.mark.asyncio
async def test_reset_zeroes_everything() -> None:
    metrics = SocialDiscoveryMetrics()
    await metrics.record_html_fetch(True)
    start = await metrics.start_one()
    await metrics.finish_one(start, instagram_found=True, facebook_found=True)

    await metrics.reset()

    snapshot = await metrics.snapshot()
    assert snapshot.total_processed == 0
    assert snapshot.html_fetch_success == 0
