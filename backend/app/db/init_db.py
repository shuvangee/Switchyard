"""Create all tables on a given engine (used at app startup and in tests)."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db.base import Base
from app.models import (  # noqa: F401 — imported so tables register on Base.metadata
    BenchmarkTaskORM,
    ExperimentRunORM,
    ModelConfigORM,
    ModelExecutionORM,
    RequestLogORM,
)

# Column -> SQL type, for columns added to an ORM model AFTER a table may
# already exist on disk. No migration tool (Alembic) exists yet at this
# project stage — create_all only creates missing TABLES, not missing
# columns on one that's already there. This keeps an existing local dev
# db (this sandbox's, or a contributor's) working across a schema change
# without deleting it. Revisit with a real migration tool if this list
# grows past a couple of entries.
_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "request_logs": [("router_score", "FLOAT")],
}


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_columns(engine)


def _add_missing_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table, columns in _ADDED_COLUMNS.items():
        if table not in existing_tables:
            continue
        existing_columns = {col["name"] for col in inspector.get_columns(table)}
        for name, sql_type in columns:
            if name not in existing_columns:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
