from datetime import timedelta

import httpx

from app.models import Platform, Post, PostStatus, utcnow
from app.scheduler import due_posts, publish_post


def make_post(session, **kwargs):
    post = Post(platform=Platform.facebook, caption="hi", **kwargs)
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


def test_due_posts_only_returns_approved_and_due(session):
    due = make_post(
        session, status=PostStatus.approved, scheduled_at=utcnow() - timedelta(minutes=1)
    )
    make_post(session, status=PostStatus.approved, scheduled_at=utcnow() + timedelta(hours=1))
    make_post(session, status=PostStatus.draft, scheduled_at=utcnow() - timedelta(hours=1))
    assert [p.id for p in due_posts(session)] == [due.id]


async def test_publish_post_marks_published(session):
    post = make_post(session, status=PostStatus.approved)
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"id": "fb-1"}))
    )
    async with client:
        result = await publish_post(post, session, client)
    assert result.status == PostStatus.published
    assert result.external_id == "fb-1"
    assert result.published_at is not None


async def test_publish_post_retries_until_attempts_exhausted(session):
    post = make_post(session, status=PostStatus.approved)
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(500, json={"error": {"message": "boom"}})
        )
    )
    async with client:
        first = await publish_post(post, session, client)
        assert first.status == PostStatus.approved and first.attempts == 1
        second = await publish_post(post, session, client)
    assert second.status == PostStatus.failed and second.attempts == 2
    assert "boom" in (second.error or "")
