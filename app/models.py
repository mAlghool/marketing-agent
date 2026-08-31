from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Platform(str, Enum):
    facebook = "facebook"
    instagram = "instagram"
    tiktok = "tiktok"


class PostStatus(str, Enum):
    draft = "draft"
    approved = "approved"
    publishing = "publishing"
    published = "published"
    failed = "failed"
    cancelled = "cancelled"


class Campaign(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    goal: str
    audience: str = ""
    brand_voice: str = ""
    language: str = "ar"
    hashtags: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Post(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    campaign_id: int | None = Field(default=None, foreign_key="campaign.id", index=True)
    platform: Platform
    caption: str
    media_url: str | None = None
    scheduled_at: datetime = Field(default_factory=utcnow, index=True)
    status: PostStatus = Field(default=PostStatus.draft, index=True)
    attempts: int = 0
    external_id: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    published_at: datetime | None = None
