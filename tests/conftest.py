import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "token")
    monkeypatch.setenv("FACEBOOK_PAGE_ID", "111")
    monkeypatch.setenv("INSTAGRAM_USER_ID", "222")
    monkeypatch.setenv("TIKTOK_ACCESS_TOKEN", "tt-token")
    monkeypatch.setenv("MAX_PUBLISH_ATTEMPTS", "2")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
