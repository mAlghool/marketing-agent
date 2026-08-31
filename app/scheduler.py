"""Polls for due posts and pushes them to the networks with bounded retries."""

from __future__ import annotations

import logging

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine
from app.models import Post, PostStatus, utcnow
from app.publishers import PublishError, get_publisher

logger = logging.getLogger(__name__)


def due_posts(session: Session) -> list[Post]:
    statement = (
        select(Post)
        .where(Post.status == PostStatus.approved, Post.scheduled_at <= utcnow())
        .order_by(Post.scheduled_at)
    )
    return list(session.exec(statement))


async def publish_post(post: Post, session: Session, client: httpx.AsyncClient) -> Post:
    settings = get_settings()
    post.status = PostStatus.publishing
    post.attempts += 1
    session.add(post)
    session.commit()
    session.refresh(post)

    try:
        post.external_id = await get_publisher(post.platform).publish(post, client)
    except (PublishError, httpx.HTTPError) as exc:
        post.error = str(exc)
        exhausted = post.attempts >= settings.max_publish_attempts
        post.status = PostStatus.failed if exhausted else PostStatus.approved
        logger.warning("publish failed for post %s (attempt %s): %s", post.id, post.attempts, exc)
    else:
        post.status = PostStatus.published
        post.published_at = utcnow()
        post.error = None

    session.add(post)
    session.commit()
    session.refresh(post)
    return post


async def run_due_posts() -> list[Post]:
    settings = get_settings()
    if not settings.publishing_enabled:
        return []
    processed: list[Post] = []
    async with httpx.AsyncClient(timeout=60) as client:
        with Session(engine) as session:
            for post in due_posts(session):
                processed.append(await publish_post(post, session, client))
    return processed


def create_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_due_posts,
        "interval",
        seconds=settings.scheduler_interval_seconds,
        id="publish-due-posts",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
