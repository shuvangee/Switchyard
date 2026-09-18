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
from app.models.request_log import RequestLogORM


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


class ModelPerformanceSummary(BaseModel):
    """Live-computed from this database's model_executions — never a fixed
    snapshot — so it's always an honest reflection of what has actually
    run here, not a baked-in historical number.
    """

    total_executions: int
    scored_executions: int
    correct: int
    avg_latency_ms: float | None
    total_cost_usd: float | None


class ModelConfigOut(BaseModel):
    id: str
    provider: str
    model_id: str
    display_name: str
    enabled: bool
    input_cost_per_1k: float
    output_cost_per_1k: float
    capabilities: dict[str, Any]
    performance: ModelPerformanceSummary | None

    @classmethod
    def from_orm_model(
        cls, model: ModelConfigORM, performance: ModelPerformanceSummary | None = None
    ) -> "ModelConfigOut":
        return cls(
            id=model.id,
            provider=model.provider,
            model_id=model.model_id,
            display_name=model.display_name,
            enabled=model.enabled,
            input_cost_per_1k=model.input_cost_per_1k,
            output_cost_per_1k=model.output_cost_per_1k,
            capabilities=model.capabilities,
            performance=performance,
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


class RouteRequest(BaseModel):
    prompt: str
    category_hint: TaskCategory | None = None


class RequestLogOut(BaseModel):
    id: str
    prompt: str
    category: str
    category_source: str
    difficulty: str
    structured_output_required: bool
    estimated_input_tokens: int
    selected_model_config_id: str
    selected_provider: str
    router_version: str
    rationale: str
    matched_rule: str | None
    status: str
    response_text: str | None
    error_message: str | None
    latency_ms: float | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    created_at: datetime

    @classmethod
    def from_orm_log(cls, log: RequestLogORM) -> "RequestLogOut":
        return cls(
            id=log.id,
            prompt=log.prompt,
            category=log.category,
            category_source=log.category_source,
            difficulty=log.difficulty,
            structured_output_required=log.structured_output_required,
            estimated_input_tokens=log.estimated_input_tokens,
            selected_model_config_id=log.selected_model_config_id,
            selected_provider=log.selected_provider,
            router_version=log.router_version,
            rationale=log.rationale,
            matched_rule=log.matched_rule,
            status=log.status,
            response_text=log.response_text,
            error_message=log.error_message,
            latency_ms=log.latency_ms,
            input_tokens=log.input_tokens,
            output_tokens=log.output_tokens,
            estimated_cost_usd=log.estimated_cost_usd,
            created_at=log.created_at,
        )


class RequestLogSummary(BaseModel):
    id: str
    prompt_preview: str
    category: str
    difficulty: str
    selected_model_config_id: str
    status: str
    latency_ms: float | None
    estimated_cost_usd: float | None
    created_at: datetime

    @classmethod
    def from_orm_log(cls, log: RequestLogORM) -> "RequestLogSummary":
        preview = log.prompt if len(log.prompt) <= 80 else log.prompt[:77] + "..."
        return cls(
            id=log.id,
            prompt_preview=preview,
            category=log.category,
            difficulty=log.difficulty,
            selected_model_config_id=log.selected_model_config_id,
            status=log.status,
            latency_ms=log.latency_ms,
            estimated_cost_usd=log.estimated_cost_usd,
            created_at=log.created_at,
        )
