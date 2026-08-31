"""Facebook Page and Instagram Business publishing via the Meta Graph API."""

from __future__ import annotations

import asyncio

import httpx

from app.config import get_settings
from app.models import Post
from app.publishers.base import Publisher, PublishError, raise_for_api_error

VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v")
CONTAINER_POLL_ATTEMPTS = 20
CONTAINER_POLL_SECONDS = 3


def graph_url(path: str) -> str:
    return f"https://graph.facebook.com/{get_settings().meta_api_version}/{path}"


def is_video(media_url: str) -> bool:
    return media_url.lower().split("?")[0].endswith(VIDEO_EXTENSIONS)


class FacebookPagePublisher(Publisher):
    def validate(self, post: Post) -> None:
        settings = get_settings()
        if not settings.meta_access_token or not settings.facebook_page_id:
            raise PublishError("META_ACCESS_TOKEN and FACEBOOK_PAGE_ID must be configured")
        if not post.caption and not post.media_url:
            raise PublishError("facebook post needs a caption or media")

    async def publish(self, post: Post, client: httpx.AsyncClient) -> str:
        self.validate(post)
        settings = get_settings()
        token = settings.meta_access_token
        if post.media_url and not is_video(post.media_url):
            response = await client.post(
                graph_url(f"{settings.facebook_page_id}/photos"),
                data={"url": post.media_url, "caption": post.caption, "access_token": token},
            )
        else:
            data = {"message": post.caption, "access_token": token}
            if post.media_url:
                data["link"] = post.media_url
            response = await client.post(graph_url(f"{settings.facebook_page_id}/feed"), data=data)
        payload = raise_for_api_error(response, "facebook")
        return str(payload.get("post_id") or payload["id"])


class InstagramPublisher(Publisher):
    def validate(self, post: Post) -> None:
        settings = get_settings()
        if not settings.meta_access_token or not settings.instagram_user_id:
            raise PublishError("META_ACCESS_TOKEN and INSTAGRAM_USER_ID must be configured")
        if not post.media_url:
            raise PublishError("instagram requires a publicly reachable media_url")

    async def publish(self, post: Post, client: httpx.AsyncClient) -> str:
        self.validate(post)
        settings = get_settings()
        token = settings.meta_access_token
        media_url = post.media_url or ""
        data = {"caption": post.caption, "access_token": token}
        if is_video(media_url):
            data |= {"media_type": "REELS", "video_url": media_url}
        else:
            data["image_url"] = media_url

        creation = raise_for_api_error(
            await client.post(graph_url(f"{settings.instagram_user_id}/media"), data=data),
            "instagram",
        )
        creation_id = str(creation["id"])
        if is_video(media_url):
            await self._await_container(creation_id, client, token)

        published = raise_for_api_error(
            await client.post(
                graph_url(f"{settings.instagram_user_id}/media_publish"),
                data={"creation_id": creation_id, "access_token": token},
            ),
            "instagram",
        )
        return str(published["id"])

    async def _await_container(
        self, creation_id: str, client: httpx.AsyncClient, token: str
    ) -> None:
        for _ in range(CONTAINER_POLL_ATTEMPTS):
            payload = raise_for_api_error(
                await client.get(
                    graph_url(creation_id),
                    params={"fields": "status_code", "access_token": token},
                ),
                "instagram",
            )
            status = payload.get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise PublishError("instagram media container failed processing")
            await asyncio.sleep(CONTAINER_POLL_SECONDS)
        raise PublishError("instagram media container timed out")
