"""Shared pytest fixtures.

Endpoint tests run against an in-memory SQLite database, isolated per test, with
the app's `get_db` dependency overridden to use it. We instantiate TestClient
without the `with` context manager so the app's lifespan (which pre-loads the
in-memory cache from the real database) does not run.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  registers every table on Base.metadata
from app import app
from core.rate_limit import limiter
from models.database import Base, get_db

# Tests register/login many times from a single host; the per-IP limits would
# otherwise trip and fail the suite. Disable rate limiting for all tests.
limiter.enabled = False


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # keep one shared connection for the in-memory DB
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def make_client(db_session):
    """Factory for fresh TestClients sharing one DB but separate cookie jars.

    Lets a test act as two distinct guests/users (each gets its own anon cookie)
    to verify one owner can't see or touch another's data.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield lambda: TestClient(app)
    finally:
        app.dependency_overrides.clear()
