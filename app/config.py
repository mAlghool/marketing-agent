from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./marketing_agent.db"
    timezone: str = "UTC"

    # Content generation
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Brand defaults, overridable per campaign
    brand_name: str = "My Brand"
    brand_voice: str = "friendly, concise, value-driven"
    brand_language: str = "ar"

    # Meta (Facebook Page + Instagram Business)
    meta_api_version: str = "v21.0"
    meta_access_token: str = ""
    facebook_page_id: str = ""
    instagram_user_id: str = ""

    # TikTok Content Posting API
    tiktok_access_token: str = ""

    # Safety switch: when false nothing is sent to the networks
    publishing_enabled: bool = False
    scheduler_interval_seconds: int = 30
    max_publish_attempts: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
