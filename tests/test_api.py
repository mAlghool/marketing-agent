import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import PostStatus


@pytest.fixture
def client(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _isolated_app_db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr("app.main.init_db", lambda: None)


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["platforms"] == ["facebook", "instagram", "tiktok"]


def test_post_lifecycle(client):
    created = client.post(
        "/api/posts", json={"platform": "facebook", "caption": "مرحبا بالعالم"}
    ).json()
    assert created["status"] == PostStatus.draft

    approved = client.post(f"/api/posts/{created['id']}/approve").json()
    assert approved["status"] == PostStatus.approved

    assert client.post(f"/api/posts/{created['id']}/approve").status_code == 409

    updated = client.patch(
        f"/api/posts/{created['id']}", json={"caption": "نص محدّث"}
    ).json()
    assert updated["caption"] == "نص محدّث"

    assert client.delete(f"/api/posts/{created['id']}").status_code == 204
    assert client.get("/api/posts", params={"status": "cancelled"}).json()[0]["id"] == created["id"]


def test_publish_blocked_when_publishing_disabled(client):
    post = client.post("/api/posts", json={"platform": "facebook", "caption": "x"}).json()
    response = client.post(f"/api/posts/{post['id']}/publish")
    assert response.status_code == 400
    assert "PUBLISHING_ENABLED" in response.json()["detail"]


def test_generate_requires_openai_key(client):
    campaign = client.post("/api/campaigns", json={"name": "c", "goal": "g"}).json()
    response = client.post(
        f"/api/campaigns/{campaign['id']}/generate", json={"platforms": ["facebook"]}
    )
    assert response.status_code == 400
