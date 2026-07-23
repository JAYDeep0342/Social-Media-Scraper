"""Request schema for a lead-search operation."""

from pydantic import BaseModel, Field, field_validator

from app.config.constants import DEFAULT_LEAD_LIMIT, MAX_LEADS


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
