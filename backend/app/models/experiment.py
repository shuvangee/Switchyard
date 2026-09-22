"""ORM tables for experiment runs and the per-task/model executions within them."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExperimentRunORM(Base):
    __tablename__ = "experiment_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    task_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    model_config_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    executions: Mapped[list["ModelExecutionORM"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ModelExecutionORM(Base):
    __tablename__ = "model_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("experiment_runs.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(ForeignKey("benchmark_tasks.id"), nullable=False)
    model_config_id: Mapped[str] = mapped_column(ForeignKey("model_configs.id"), nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False)
    response_text: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    evaluation_status: Mapped[str] = mapped_column(String, nullable=False)
    evaluation_detail: Mapped[str | None] = mapped_column(String, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    run: Mapped["ExperimentRunORM"] = relationship(back_populates="executions")
