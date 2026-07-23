import pytest

from app.discovery.google_maps.pipeline import run_discovery
from tests.discovery.google_maps.fakes import FakeCard, FakePage


def _card(i: int, *, dup_of: int = None) -> FakeCard:
    place_id_source = dup_of if dup_of is not None else i
    return FakeCard(
        name=f"Business {i}",
        maps_url=f"https://maps.google.com/place/Business+{i}/data=!1s0x{place_id_source}:0x{place_id_source}",
    )


@pytest.mark.asyncio
async def test_run_discovery_end_to_end_with_dedup() -> None:
    # index 2 shares index 1's place id -> should be removed by DeduplicateStage
    cards = [_card(0), _card(1), _card(2, dup_of=1), _card(3)]
    page = FakePage(cards=cards, reveal_schedule=[4])

    result = await run_discovery(page, keyword="coffee shops", location="Seattle, WA", limit=4)

    names = [lead.business_name for lead in result.leads]
    assert names == ["Business 0", "Business 1", "Business 3"]
    assert all(lead.source_keyword == "coffee shops" for lead in result.leads)
    assert all(lead.source_location == "Seattle, WA" for lead in result.leads)

    assert result.metrics.cards_collected == 3
    assert result.metrics.duplicate_count == 1
    assert result.metrics.scroll_count == 0
    assert result.metrics.discovery_time_seconds >= 0
    assert result.metrics.cards_per_second >= 0


@pytest.mark.asyncio
async def test_run_discovery_with_no_duplicates() -> None:
    cards = [_card(0), _card(1), _card(2)]
    page = FakePage(cards=cards, reveal_schedule=[3])

    result = await run_discovery(page, keyword="bakeries", location="Portland, OR", limit=3)

    assert len(result.leads) == 3
    assert result.metrics.duplicate_count == 0


@pytest.mark.asyncio
async def test_run_discovery_scrolls_when_more_cards_needed_than_initially_revealed() -> None:
    cards = [_card(i) for i in range(20)]
    page = FakePage(cards=cards, reveal_schedule=[6, 12, 20])

    result = await run_discovery(
        page, keyword="coffee shops", location="Seattle, WA", limit=15, scroll_base_pause_seconds=0.01
    )

    assert result.metrics.cards_collected == 15  # truncated to the requested limit
    assert result.metrics.scroll_count == 2  # 6 -> 12 -> 20 (limit met after 2nd scroll)
