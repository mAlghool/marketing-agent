from datetime import datetime

from pydantic import BaseModel, Field

from app.models import Platform, PostStatus


class CampaignCreate(BaseModel):
    name: str
    goal: str
    audience: str = ""
    brand_voice: str = ""
    language: str = "ar"
    hashtags: str = ""


class GenerateRequest(BaseModel):
    platforms: list[Platform]
    count_per_platform: int = Field(default=1, ge=1, le=5)
    start_at: datetime | None = None
    interval_hours: int = Field(default=24, ge=0, le=24 * 30)
    media_url: str | None = None
    auto_approve: bool = False


class PostCreate(BaseModel):
    platform: Platform
    caption: str
    media_url: str | None = None
    scheduled_at: datetime | None = None
    campaign_id: int | None = None
    approved: bool = False


class PostUpdate(BaseModel):
    caption: str | None = None
    media_url: str | None = None
    scheduled_at: datetime | None = None
    status: PostStatus | None = None
