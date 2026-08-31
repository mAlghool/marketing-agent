import httpx
import pytest

from app.models import Platform, Post
from app.publishers import PublishError, get_publisher


def transport(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_facebook_photo_post_uses_photos_edge():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"id": "1_2", "post_id": "111_222"})

    post = Post(platform=Platform.facebook, caption="hi", media_url="https://x.test/a.jpg")
    async with transport(handler) as client:
        assert await get_publisher(Platform.facebook).publish(post, client) == "111_222"
    assert seen["url"].endswith("/111/photos")


async def test_facebook_text_post_uses_feed_edge():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/111/feed")
        return httpx.Response(200, json={"id": "111_333"})

    post = Post(platform=Platform.facebook, caption="text only")
    async with transport(handler) as client:
        assert await get_publisher(Platform.facebook).publish(post, client) == "111_333"


async def test_instagram_creates_container_then_publishes():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "container-1"})
        return httpx.Response(200, json={"id": "ig-99"})

    post = Post(platform=Platform.instagram, caption="c", media_url="https://x.test/a.jpg")
    async with transport(handler) as client:
        assert await get_publisher(Platform.instagram).publish(post, client) == "ig-99"
    assert calls[0].endswith("/222/media") and calls[1].endswith("/222/media_publish")


async def test_instagram_requires_media():
    post = Post(platform=Platform.instagram, caption="no media")
    with pytest.raises(PublishError, match="media_url"):
        get_publisher(Platform.instagram).validate(post)


async def test_tiktok_returns_publish_id():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer tt-token"
        return httpx.Response(200, json={"data": {"publish_id": "pub-7"}, "error": {"code": "ok"}})

    post = Post(platform=Platform.tiktok, caption="hook", media_url="https://x.test/v.mp4")
    async with transport(handler) as client:
        assert await get_publisher(Platform.tiktok).publish(post, client) == "pub-7"


async def test_api_error_raises_publish_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "bad token"}})

    post = Post(platform=Platform.facebook, caption="hi")
    async with transport(handler) as client:
        with pytest.raises(PublishError, match="bad token"):
            await get_publisher(Platform.facebook).publish(post, client)
