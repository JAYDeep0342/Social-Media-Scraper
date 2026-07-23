import pytest

from app.enrichment.google_maps.detail_navigator import DetailPanelNavigator
from app.exceptions.errors import ExtractionError, ScraperTimeoutError
from app.exceptions.network import RetryExceeded
from app.network.retry_strategy import RetryPolicy
from tests.enrichment.google_maps.fakes import FakeDetailPage

_FAST_POLICY = RetryPolicy(
    max_attempts=3, base_delay=0.01, max_delay=0.02, jitter=0.0, retryable_exceptions=(ScraperTimeoutError, ExtractionError)
)


@pytest.mark.asyncio
async def test_open_navigates_and_waits_for_panel() -> None:
    page = FakeDetailPage()
    navigator = DetailPanelNavigator(page, retry_policy=_FAST_POLICY)

    await navigator.open("https://maps.google.com/place/x/data=!1s0x1:0x1")

    call_kinds = [call[0] for call in page.calls]
    assert call_kinds == ["goto", "wait_for_selector"]


@pytest.mark.asyncio
async def test_open_retries_transient_failures_then_succeeds() -> None:
    page = FakeDetailPage(transient_failures=2)
    navigator = DetailPanelNavigator(page, retry_policy=_FAST_POLICY)

    await navigator.open("https://maps.google.com/place/x/data=!1s0x1:0x1")

    assert page._wait_attempts == 3


@pytest.mark.asyncio
async def test_open_raises_retry_exceeded_after_exhausting_attempts() -> None:
    page = FakeDetailPage(fail_open=True)
    navigator = DetailPanelNavigator(page, retry_policy=_FAST_POLICY)

    with pytest.raises(RetryExceeded):
        await navigator.open("https://maps.google.com/place/x/data=!1s0x1:0x1")
