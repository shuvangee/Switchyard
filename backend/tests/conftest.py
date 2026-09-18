"""Shared pytest fixtures: an isolated in-memory database per test."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks, sync_benchmark_tasks
from app.main import app
from app.providers.registry import sync_model_configs


def _make_in_memory_session() -> tuple[Session, Engine]:
    """StaticPool keeps a single connection alive for the engine's lifetime
    so the in-memory database survives across multiple sessions/connections.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory(), engine


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """A fresh in-memory SQLite database, isolated per test."""
    session, engine = _make_in_memory_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def api_client() -> Generator[TestClient, None, None]:
    """A TestClient backed by an isolated, pre-seeded in-memory database.

    Deliberately NOT used as `with TestClient(app) as client` — that would
    run app.main's real lifespan, which syncs into the *production*
    settings-derived engine. Instead this fixture seeds an isolated
    database directly and overrides the get_db dependency, so the app's
    own startup/shutdown events never run during tests.
    """
    session, engine = _make_in_memory_session()
    tasks = load_benchmark_tasks(default_benchmarks_dir())
    sync_benchmark_tasks(session, tasks)
    sync_model_configs(session, Settings(openai_api_key=None))

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        engine.dispose()
