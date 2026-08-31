from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.agent import ContentAgent
from app.config import get_settings
from app.db import get_session, init_db
from app.models import Campaign, Platform, Post, PostStatus, utcnow
from app.publishers import PublishError
from app.scheduler import create_scheduler, publish_post
from app.schemas import CampaignCreate, GenerateRequest, PostCreate, PostUpdate

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = create_scheduler()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Marketing Agent", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "publishing_enabled": settings.publishing_enabled,
        "platforms": [p.value for p in Platform],
    }


@app.post("/api/campaigns", response_model=Campaign, status_code=201)
def create_campaign(payload: CampaignCreate, session: Session = Depends(get_session)) -> Campaign:
    campaign = Campaign(**payload.model_dump())
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


@app.get("/api/campaigns", response_model=list[Campaign])
def list_campaigns(session: Session = Depends(get_session)) -> list[Campaign]:
    return list(session.exec(select(Campaign).order_by(Campaign.id.desc())))


@app.post("/api/campaigns/{campaign_id}/generate", response_model=list[Post], status_code=201)
async def generate_posts(
    campaign_id: int,
    payload: GenerateRequest,
    session: Session = Depends(get_session),
) -> list[Post]:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    if not get_settings().openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured")

    generated = await ContentAgent().generate(
        campaign, payload.platforms, payload.count_per_platform
    )
    start = payload.start_at or utcnow()
    posts: list[Post] = []
    for index, item in enumerate(generated):
        post = Post(
            campaign_id=campaign_id,
            platform=item.platform,
            caption=item.caption,
            media_url=payload.media_url,
            scheduled_at=start + timedelta(hours=payload.interval_hours * index),
            status=PostStatus.approved if payload.auto_approve else PostStatus.draft,
        )
        session.add(post)
        posts.append(post)
    session.commit()
    for post in posts:
        session.refresh(post)
    return posts


@app.post("/api/posts", response_model=Post, status_code=201)
def create_post(payload: PostCreate, session: Session = Depends(get_session)) -> Post:
    post = Post(
        campaign_id=payload.campaign_id,
        platform=payload.platform,
        caption=payload.caption,
        media_url=payload.media_url,
        scheduled_at=payload.scheduled_at or utcnow(),
        status=PostStatus.approved if payload.approved else PostStatus.draft,
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@app.get("/api/posts", response_model=list[Post])
def list_posts(
    status: PostStatus | None = None,
    platform: Platform | None = None,
    session: Session = Depends(get_session),
) -> list[Post]:
    statement = select(Post).order_by(Post.scheduled_at)
    if status is not None:
        statement = statement.where(Post.status == status)
    if platform is not None:
        statement = statement.where(Post.platform == platform)
    return list(session.exec(statement))


def _get_post(post_id: int, session: Session) -> Post:
    post = session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    return post


@app.patch("/api/posts/{post_id}", response_model=Post)
def update_post(
    post_id: int, payload: PostUpdate, session: Session = Depends(get_session)
) -> Post:
    post = _get_post(post_id, session)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(post, field, value)
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@app.post("/api/posts/{post_id}/approve", response_model=Post)
def approve_post(post_id: int, session: Session = Depends(get_session)) -> Post:
    post = _get_post(post_id, session)
    if post.status not in (PostStatus.draft, PostStatus.failed):
        raise HTTPException(
            status_code=409, detail=f"cannot approve a post with status '{post.status.value}'"
        )
    post.status = PostStatus.approved
    post.attempts = 0
    post.error = None
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@app.post("/api/posts/{post_id}/publish", response_model=Post)
async def publish_now(post_id: int, session: Session = Depends(get_session)) -> Post:
    settings = get_settings()
    if not settings.publishing_enabled:
        raise HTTPException(status_code=400, detail="publishing is disabled (PUBLISHING_ENABLED)")
    post = _get_post(post_id, session)
    if post.status == PostStatus.published:
        raise HTTPException(status_code=409, detail="post is already published")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            return await publish_post(post, session, client)
    except PublishError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.delete("/api/posts/{post_id}", status_code=204)
def cancel_post(post_id: int, session: Session = Depends(get_session)) -> None:
    post = _get_post(post_id, session)
    post.status = PostStatus.cancelled
    session.add(post)
    session.commit()
