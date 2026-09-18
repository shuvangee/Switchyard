"""Benchmark task: the Pydantic schema used to author/validate task files,
and the ORM table used to query and join them at runtime.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import EvaluationType, TaskCategory, TaskDifficulty


class BenchmarkTaskSchema(BaseModel):
    """Shape of a benchmark task file under benchmarks/tasks/*.json."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    category: TaskCategory
    difficulty: TaskDifficulty
    prompt: str
    evaluation_type: EvaluationType
    expected_output: str | None = None
    metadata: dict[str, Any] = {}


class BenchmarkTaskORM(Base):
    __tablename__ = "benchmark_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[str] = mapped_column(String, nullable=False)
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    evaluation_type: Mapped[str] = mapped_column(String, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(String, nullable=True)
    task_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
