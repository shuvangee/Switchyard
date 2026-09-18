"""Pydantic request/response schemas for the HTTP API.

Kept separate from the ORM models so the API contract can evolve
independently of the persistence schema.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.benchmark import BenchmarkTaskORM
from app.models.enums import TaskCategory
from app.models.experiment import ModelExecutionORM
from app.models.model_config import ModelConfigORM


class BenchmarkTaskOut(BaseModel):
    id: str
    title: str
    category: str
    difficulty: str
    prompt: str
    evaluation_type: str
    expected_output: str | None
    metadata: dict[str, Any]

    @classmethod
    def from_orm_task(cls, task: BenchmarkTaskORM) -> "BenchmarkTaskOut":
        return cls(
            id=task.id,
            title=task.title,
            category=task.category,
            difficulty=task.difficulty,
            prompt=task.prompt,
            evaluation_type=task.evaluation_type,
            expected_output=task.expected_output,
            metadata=task.task_metadata,
        )


class ModelConfigOut(BaseModel):
    id: str
    provider: str
    model_id: str
    display_name: str
    enabled: bool
    input_cost_per_1k: float
    output_cost_per_1k: float
    capabilities: dict[str, Any]

    @classmethod
    def from_orm_model(cls, model: ModelConfigORM) -> "ModelConfigOut":
        return cls(
            id=model.id,
            provider=model.provider,
            model_id=model.model_id,
            display_name=model.display_name,
            enabled=model.enabled,
            input_cost_per_1k=model.input_cost_per_1k,
            output_cost_per_1k=model.output_cost_per_1k,
            capabilities=model.capabilities,
        )


class ModelExecutionOut(BaseModel):
    id: int
    task_id: str
    model_config_id: str
    provider: str
    status: str
    response_text: str | None
    error_message: str | None
    latency_ms: float | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    evaluation_status: str
    evaluation_detail: str | None
    started_at: datetime
    completed_at: datetime

    @classmethod
    def from_orm_execution(cls, execution: ModelExecutionORM, provider: str) -> "ModelExecutionOut":
        return cls(
            id=execution.id,
            task_id=execution.task_id,
            model_config_id=execution.model_config_id,
            provider=provider,
            status=execution.status,
            response_text=execution.response_text,
            error_message=execution.error_message,
            latency_ms=execution.latency_ms,
            input_tokens=execution.input_tokens,
            output_tokens=execution.output_tokens,
            estimated_cost_usd=execution.estimated_cost_usd,
            evaluation_status=execution.evaluation_status,
            evaluation_detail=execution.evaluation_detail,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )


class ExperimentRunSummary(BaseModel):
    id: str
    name: str | None
    status: str
    task_count: int
    model_count: int
    execution_count: int
    created_at: datetime
    completed_at: datetime | None


class ExperimentRunDetail(BaseModel):
    id: str
    name: str | None
    status: str
    task_ids: list[str]
    model_config_ids: list[str]
    created_at: datetime
    completed_at: datetime | None
    executions: list[ModelExecutionOut]


class CreateExperimentRequest(BaseModel):
    task_ids: list[str] | None = None
    category: TaskCategory | None = None
    model_config_ids: list[str]
    name: str | None = None
