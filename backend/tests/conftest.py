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
from models.database import Base, get_db


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
