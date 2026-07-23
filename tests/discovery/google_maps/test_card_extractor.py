import pytest

from app.discovery.google_maps.card_extractor import CardExtractor
from tests.discovery.google_maps.fakes import FakeCard, FakePage


@pytest.mark.asyncio
async def test_extracts_name_and_maps_url_website_none_when_absent() -> None:
    card = FakeCard(name="Storyville Coffee", maps_url="https://maps.google.com/place/x/data=!1s0x1:0x1")
    page = FakePage(cards=[card])
    extractor = CardExtractor(page)

    leads = await extractor.extract_all(source_keyword="coffee", source_location="Seattle")

    assert len(leads) == 1
    lead = leads[0]
    assert lead.business_name == "Storyville Coffee"
    assert lead.social.google_maps_url == card.maps_url
    assert lead.website is None
    assert lead.source_keyword == "coffee"
    assert lead.source_location == "Seattle"


@pytest.mark.asyncio
async def test_extracts_website_when_visible_on_card() -> None:
    card = FakeCard(website="https://example-coffee.com/")
    page = FakePage(cards=[card])
    extractor = CardExtractor(page)

    leads = await extractor.extract_all(source_keyword="coffee", source_location="Seattle")

    assert leads[0].website == "https://example-coffee.com"


@pytest.mark.asyncio
async def test_falls_back_to_class_name_when_aria_label_missing() -> None:
    card = FakeCard(name="Overcast Coffee", name_only_via_class=True)
    page = FakePage(cards=[card])
    extractor = CardExtractor(page)

    leads = await extractor.extract_all(source_keyword="coffee", source_location="Seattle")

    assert leads[0].business_name == "Overcast Coffee"


@pytest.mark.asyncio
async def test_skips_card_with_no_link() -> None:
    good = FakeCard(name="Good Business")
    bad = FakeCard(no_link=True)
    page = FakePage(cards=[bad, good])
    extractor = CardExtractor(page)

    leads = await extractor.extract_all(source_keyword="coffee", source_location="Seattle")

    assert len(leads) == 1
    assert leads[0].business_name == "Good Business"


@pytest.mark.asyncio
async def test_skips_card_with_no_name_at_all() -> None:
    card = FakeCard(name=None, name_only_via_class=False)
    page = FakePage(cards=[card])
    extractor = CardExtractor(page)

    leads = await extractor.extract_all(source_keyword="coffee", source_location="Seattle")

    assert leads == []


@pytest.mark.asyncio
async def test_no_phone_rating_or_address_fields_exist_on_lead() -> None:
    card = FakeCard()
    page = FakePage(cards=[card])
    extractor = CardExtractor(page)

    leads = await extractor.extract_all(source_keyword="coffee", source_location="Seattle")
    lead_fields = leads[0].to_dict().keys()

    assert "phone" not in lead_fields
    assert "rating" not in lead_fields
    assert "address" not in lead_fields
