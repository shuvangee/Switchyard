"""Loads and validates benchmark task files, and syncs them into the DB.

Benchmark tasks are authored as JSON files under benchmarks/tasks/ (see
that directory's README for the format) — that's the git-tracked source of
truth. The DB table is a synced, queryable copy: sync_benchmark_tasks()
upserts by id so the DB always reflects whatever files are currently on
disk.
"""

import json
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.time import utcnow
from app.models.benchmark import BenchmarkTaskORM, BenchmarkTaskSchema


class BenchmarkLoadError(Exception):
    """Raised when a benchmark task file is missing, malformed, or duplicated."""


def default_benchmarks_dir() -> Path:
    # backend/app/experiments/loader.py -> repo root is 3 levels up from
    # backend/app/experiments, i.e. parents[2] == backend/, parents[3] == repo root.
    return Path(__file__).resolve().parents[3] / "benchmarks" / "tasks"


def get_benchmarks_dir(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    if settings.benchmarks_dir:
        return Path(settings.benchmarks_dir)
    return default_benchmarks_dir()


def load_benchmark_tasks(directory: Path) -> list[BenchmarkTaskSchema]:
    if not directory.exists():
        raise BenchmarkLoadError(f"benchmarks directory not found: {directory}")

    tasks: list[BenchmarkTaskSchema] = []
    seen_ids: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(path.read_text())
            task = BenchmarkTaskSchema.model_validate(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise BenchmarkLoadError(f"invalid benchmark task file {path.name}: {exc}") from exc
        if task.id != path.stem:
            raise BenchmarkLoadError(
                f"task id {task.id!r} in {path.name} does not match filename {path.stem!r}"
            )
        if task.id in seen_ids:
            raise BenchmarkLoadError(f"duplicate benchmark task id: {task.id!r}")
        seen_ids.add(task.id)
        tasks.append(task)
    return tasks


def sync_benchmark_tasks(session: Session, tasks: list[BenchmarkTaskSchema]) -> None:
    now = utcnow()
    for task in tasks:
        existing = session.get(BenchmarkTaskORM, task.id)
        if existing is None:
            existing = BenchmarkTaskORM(id=task.id, created_at=now)
            session.add(existing)
        existing.title = task.title
        existing.category = task.category.value
        existing.difficulty = task.difficulty.value
        existing.prompt = task.prompt
        existing.evaluation_type = task.evaluation_type.value
        existing.expected_output = task.expected_output
        existing.task_metadata = task.metadata
        existing.updated_at = now
    session.commit()
