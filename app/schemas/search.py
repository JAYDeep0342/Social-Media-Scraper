"""Request/response schemas for a lead-search operation."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.config.constants import DEFAULT_LEAD_LIMIT, MAX_LEADS
from app.models.domain import BusinessLead


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=2, max_length=200, description="Search keyword, e.g. 'plumbers'")
    location: str = Field(..., min_length=2, max_length=200, description="Target location, e.g. 'Austin, TX'")
    limit: int = Field(
        default=DEFAULT_LEAD_LIMIT,
        ge=1,
        le=MAX_LEADS,
        description="Maximum number of leads to return",
    )

    @field_validator("keyword", "location")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class SocialLinksOut(BaseModel):
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    google_maps_url: Optional[str] = None
    instagram_confidence: Optional[str] = None
    facebook_confidence: Optional[str] = None


class LeadOut(BaseModel):
    business_name: str
    website: Optional[str] = None
    social: SocialLinksOut
    source_keyword: Optional[str] = None
    source_location: Optional[str] = None
    discovered_at: datetime

    @classmethod
    def from_domain(cls, lead: BusinessLead) -> "LeadOut":
        return cls(
            business_name=lead.business_name,
            website=lead.website,
            social=SocialLinksOut(
                instagram_url=lead.social.instagram_url,
                facebook_url=lead.social.facebook_url,
                google_maps_url=lead.social.google_maps_url,
                instagram_confidence=lead.social.instagram_confidence,
                facebook_confidence=lead.social.facebook_confidence,
            ),
            source_keyword=lead.source_keyword,
            source_location=lead.source_location,
            discovered_at=lead.discovered_at,
        )


class MetricsOut(BaseModel):
    stage_times: Dict[str, float]
    overall_seconds: float
    throughput_per_second: float
    success_rate: float


class ProgressOut(BaseModel):
    current_stage: Optional[str]
    completed_businesses: int
    failed_businesses: int
    elapsed_seconds: float


class SearchResult(BaseModel):
    leads: List[LeadOut]
    total: int
    metrics: MetricsOut
    progress: ProgressOut
