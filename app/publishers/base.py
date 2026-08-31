from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.models import Post


class PublishError(RuntimeError):
    """Raised when a network refuses or fails a publish request."""


class Publisher(ABC):
    """Publishes a single post to one social network and returns its external id."""

    @abstractmethod
    async def publish(self, post: Post, client: httpx.AsyncClient) -> str: ...

    @abstractmethod
    def validate(self, post: Post) -> None:
        """Raise PublishError if the post cannot be published to this network."""


def raise_for_api_error(
    response: httpx.Response, network: str, error_key: str | None = "error"
) -> dict:
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    if response.is_error or (error_key is not None and payload.get(error_key)):
        raise PublishError(f"{network} API error ({response.status_code}): {payload}")
    return payload
