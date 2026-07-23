import pytest

from app.discovery.google_maps.scroll_engine import ScrollEngine
from tests.discovery.google_maps.fakes import FakeCard, FakePage


def _cards(n: int):
    return [FakeCard(name=f"Business {i}", maps_url=f"https://maps.google.com/place/{i}/data=!1s0x{i}:0x{i}") for i in range(n)]


@pytest.mark.asyncio
async def test_stops_when_limit_reached_without_scrolling() -> None:
    page = FakePage(cards=_cards(20), reveal_schedule=[20])
    engine = ScrollEngine(page, base_pause_seconds=0.01)

    result = engine
    result = await engine.scroll_until(limit=10)

    assert result.reached_limit is True
    assert result.scroll_count == 0


@pytest.mark.asyncio
async def test_scrolls_until_limit_reached() -> None:
    page = FakePage(cards=_cards(30), reveal_schedule=[6, 12, 20, 30])
    engine = ScrollEngine(page, base_pause_seconds=0.01)

    result = await engine.scroll_until(limit=20)

    assert result.reached_limit is True
    assert result.scroll_count == 2  # 6 -> 12 -> 20 (limit met right after 2nd scroll)


@pytest.mark.asyncio
async def test_detects_end_of_list_via_stalled_count() -> None:
    page = FakePage(cards=_cards(20), reveal_schedule=[6, 12, 20, 20, 20, 20])
    engine = ScrollEngine(page, base_pause_seconds=0.01, max_attempts_without_progress=3)

    result = await engine.scroll_until(limit=100)  # unreachable given the dataset

    assert result.reached_end_of_list is True
    assert result.reached_limit is False


@pytest.mark.asyncio
async def test_stops_at_max_total_attempts_as_a_safety_cap() -> None:
    # Progress never stalls long enough to trip max_stall, but also never
    # reaches the limit -> the hard safety cap must still terminate the loop.
    schedule = list(range(1, 200))
    page = FakePage(cards=_cards(200), reveal_schedule=schedule)
    engine = ScrollEngine(page, base_pause_seconds=0.001, max_attempts_without_progress=1000, max_total_attempts=5)

    result = await engine.scroll_until(limit=1000)

    assert result.scroll_count == 5
    assert result.reached_limit is False
    assert result.reached_end_of_list is False


@pytest.mark.asyncio
async def test_detects_end_of_list_via_text_marker() -> None:
    page = FakePage(cards=_cards(6), reveal_schedule=[6], simulate_end_marker_after=0)
    engine = ScrollEngine(page, base_pause_seconds=0.01)

    result = await engine.scroll_until(limit=100)

    assert result.reached_end_of_list is True
    assert result.scroll_count == 0
