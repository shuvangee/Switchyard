"""Shared pytest fixtures: an isolated in-memory database per test."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.init_db import init_db


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """A fresh in-memory SQLite database, isolated per test.

    StaticPool keeps a single connection alive for the lifetime of the
    engine so the in-memory database survives across the multiple
    sessions/connections SQLAlchemy and FastAPI may open during a test.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
