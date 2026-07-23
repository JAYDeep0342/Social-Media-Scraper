from app.discovery.google_maps.dedup import deduplicate_leads, extract_place_id
from app.models.domain import BusinessLead, SocialLead

_URL_A = "https://www.google.com/maps/place/A/data=!4m7!3m6!1s0x54906ab2f0c61d05:0x771b2a7dce963d58!8m2"
_URL_A_DIFFERENT_QUERY = _URL_A.replace("data=", "data=") + "?authuser=1&hl=en"
_URL_B = "https://www.google.com/maps/place/B/data=!4m7!3m6!1s0x1234:0x5678!8m2"


def test_extract_place_id_from_real_url_format() -> None:
    assert extract_place_id(_URL_A) == "0x54906ab2f0c61d05:0x771b2a7dce963d58"


def test_extract_place_id_returns_none_when_absent() -> None:
    assert extract_place_id("https://example.com/no-place-id-here") is None


def test_deduplicate_removes_same_place_id_despite_query_string_diff() -> None:
    leads = [
        BusinessLead(business_name="A", social=SocialLead(google_maps_url=_URL_A)),
        BusinessLead(business_name="A duplicate", social=SocialLead(google_maps_url=_URL_A_DIFFERENT_QUERY)),
        BusinessLead(business_name="B", social=SocialLead(google_maps_url=_URL_B)),
    ]

    unique, duplicate_count = deduplicate_leads(leads)

    assert len(unique) == 2
    assert duplicate_count == 1
    assert unique[0].business_name == "A"  # first occurrence kept
    assert unique[1].business_name == "B"


def test_leads_without_maps_url_are_kept_not_deduplicated_away() -> None:
    leads = [
        BusinessLead(business_name="No URL 1", social=SocialLead(google_maps_url=None)),
        BusinessLead(business_name="No URL 2", social=SocialLead(google_maps_url=None)),
    ]

    unique, duplicate_count = deduplicate_leads(leads)

    assert len(unique) == 2
    assert duplicate_count == 0


def test_no_duplicates_returns_zero_count() -> None:
    leads = [
        BusinessLead(business_name="A", social=SocialLead(google_maps_url=_URL_A)),
        BusinessLead(business_name="B", social=SocialLead(google_maps_url=_URL_B)),
    ]

    unique, duplicate_count = deduplicate_leads(leads)

    assert len(unique) == 2
    assert duplicate_count == 0
