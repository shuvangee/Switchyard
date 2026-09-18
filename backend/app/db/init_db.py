"""Create all tables on a given engine (used at app startup and in tests)."""

from sqlalchemy.engine import Engine

from app.db.base import Base
from app.models import (  # noqa: F401 — imported so tables register on Base.metadata
    BenchmarkTaskORM,
    ExperimentRunORM,
    ModelConfigORM,
    ModelExecutionORM,
)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
