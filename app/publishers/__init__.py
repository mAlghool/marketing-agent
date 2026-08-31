from app.models import Platform
from app.publishers.base import Publisher, PublishError
from app.publishers.meta import FacebookPagePublisher, InstagramPublisher
from app.publishers.tiktok import TikTokPublisher

PUBLISHERS: dict[Platform, Publisher] = {
    Platform.facebook: FacebookPagePublisher(),
    Platform.instagram: InstagramPublisher(),
    Platform.tiktok: TikTokPublisher(),
}


def get_publisher(platform: Platform) -> Publisher:
    return PUBLISHERS[platform]


__all__ = [
    "PUBLISHERS",
    "FacebookPagePublisher",
    "InstagramPublisher",
    "PublishError",
    "Publisher",
    "TikTokPublisher",
    "get_publisher",
]
