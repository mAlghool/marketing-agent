"""TikTok publishing via the Content Posting API (PULL_FROM_URL)."""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.models import Post
from app.publishers.base import Publisher, PublishError, raise_for_api_error

INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
CAPTION_LIMIT = 2200


class TikTokPublisher(Publisher):
    def validate(self, post: Post) -> None:
        if not get_settings().tiktok_access_token:
            raise PublishError("TIKTOK_ACCESS_TOKEN must be configured")
        if not post.media_url:
            raise PublishError("tiktok requires a video media_url")
        if len(post.caption) > CAPTION_LIMIT:
            raise PublishError(f"tiktok caption exceeds {CAPTION_LIMIT} characters")

    async def publish(self, post: Post, client: httpx.AsyncClient) -> str:
        self.validate(post)
        response = await client.post(
            INIT_URL,
            headers={
                "Authorization": f"Bearer {get_settings().tiktok_access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "post_info": {
                    "title": post.caption,
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": post.media_url,
                },
            },
        )
        payload = raise_for_api_error(response, "tiktok", error_key=None)
        error = payload.get("error") or {}
        if error.get("code") not in (None, "ok"):
            raise PublishError(f"tiktok API error: {error}")
        return str(payload["data"]["publish_id"])
