"""Framework-agnostic domain models.

These are plain dataclasses (not Pydantic) because they represent internal
business objects passed between future services/extractors/parsers, not
API request/response payloads.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(slots=True)
class SocialLead:
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    google_maps_url: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "instagram_url": self.instagram_url,
            "facebook_url": self.facebook_url,
            "google_maps_url": self.google_maps_url,
        }


@dataclass(slots=True)
class BusinessLead:
    business_name: str
    website: Optional[str] = None
    social: SocialLead = field(default_factory=SocialLead)
    source_keyword: Optional[str] = None
    source_location: Optional[str] = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_name": self.business_name,
            "website": self.website,
            "instagram_url": self.social.instagram_url,
            "facebook_url": self.social.facebook_url,
            "google_maps_url": self.social.google_maps_url,
            "source_keyword": self.source_keyword,
            "source_location": self.source_location,
            "discovered_at": self.discovered_at.isoformat(),
        }
