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


class CategoryCoverage(BaseModel):
    category: str
    total: int
    auto_graded: int
    manual_only: int
    ungraded: int


class EvaluationCoverageOut(BaseModel):
    """Real coverage of the 104-task benchmark, sourced from the same
    committed results file as BenchmarkPerformanceSummary — never
    recomputed from live traffic, since evaluation coverage is a
    property of the offline research benchmark, not this deployment.
    """

    total_tasks: int
    auto_graded: int
    manual_only: int
    ungraded: int
    automated_pct: float | None
    by_category: list[CategoryCoverage]


class ModelPerformanceSummary(BaseModel):
    """Live-computed from THIS DEPLOYMENT's own model_executions table —
    never a fixed snapshot, and null on a fresh install with no traffic
    yet. Distinct from BenchmarkPerformanceSummary below — this is what
    has actually run on this instance, not the offline research result.
    """

    total_executions: int
    scored_executions: int
    correct: int
    avg_latency_ms: float | None
    total_cost_usd: float | None


class BenchmarkPerformanceSummary(BaseModel):
    """Real, measured results from the committed 92-task offline Groq
    benchmark (experiments/results/groq-gpt-oss-expansion.json) — the
    same numbers documented throughout docs/case-study/. Present only
    for models actually included in that benchmark (currently
    groq-gpt-oss-20b/120b); null for every other model, never estimated
    or backfilled.
    """

    n_executions: int
    n_graded: int
    n_correct: int
    accuracy: float | None
    avg_latency_ms: float | None
    nominal_cost_usd: float | None


class CategoryAccuracy(BaseModel):
    category: str
    n_graded: int
    n_correct: int
    accuracy: float


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
    benchmark_performance: BenchmarkPerformanceSummary | None
    benchmark_performance_by_category: list[CategoryAccuracy] | None

    @classmethod
    def from_orm_model(
        cls,
        model: ModelConfigORM,
        performance: ModelPerformanceSummary | None = None,
        benchmark_performance: BenchmarkPerformanceSummary | None = None,
        benchmark_performance_by_category: list[CategoryAccuracy] | None = None,
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
            benchmark_performance=benchmark_performance,
            benchmark_performance_by_category=benchmark_performance_by_category,
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
    # "d2-baseline" (preferred production strategy — see
    # docs/case-study/DECISIONS.md 2026-09-24/27), "learned-v2" (V3's
    # trained escalation classifier — does not currently beat
    # d2-baseline), "always-20b" / "always-120b" (fixed single-model
    # baselines, for direct comparison), "v2" (default, rule-based,
    # mock-tier models — pre-V3), or "learned-v1" (earlier exploratory
    # multiclass model — not recommended, see EXPERIMENTS.md 2026-09-22).
    router_version: str | None = None
    # Optional "bring your own key" Groq API key, scoped to this one
    # request only. Lets a deployment with no server-side GROQ_API_KEY
    # still offer real live routing to a caller who supplies their own —
    # never persisted to RequestLogOut/RequestLogSummary, never written
    # to a trace event, never logged. See docs/case-study/DECISIONS.md
    # (2026-09-28, "bring your own key").
    groq_api_key: str | None = None


class TraceEventOut(BaseModel):
    event_type: str
    detail: str
    timestamp: str


class RequestLogOut(BaseModel):
    id: str
    prompt: str
    category: str
    category_source: str
    difficulty: str
    structured_output_required: bool
    estimated_input_tokens: int
    confidence: str
    initial_model_config_id: str
    selected_model_config_id: str
    selected_provider: str
    router_version: str
    rationale: str
    matched_rule: str | None
    router_score: float | None
    escalated: bool
    attempt_count: int
    validation_status: str
    validation_detail: str | None
    status: str
    response_text: str | None
    error_message: str | None
    latency_ms: float | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    trace_events: list[TraceEventOut]
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
            confidence=log.confidence,
            initial_model_config_id=log.initial_model_config_id,
            selected_model_config_id=log.selected_model_config_id,
            selected_provider=log.selected_provider,
            router_version=log.router_version,
            rationale=log.rationale,
            matched_rule=log.matched_rule,
            router_score=log.router_score,
            escalated=log.escalated,
            attempt_count=log.attempt_count,
            validation_status=log.validation_status,
            validation_detail=log.validation_detail,
            status=log.status,
            response_text=log.response_text,
            error_message=log.error_message,
            latency_ms=log.latency_ms,
            input_tokens=log.input_tokens,
            output_tokens=log.output_tokens,
            estimated_cost_usd=log.estimated_cost_usd,
            trace_events=[TraceEventOut(**event) for event in log.trace_events],
            created_at=log.created_at,
        )


class RequestLogSummary(BaseModel):
    id: str
    prompt_preview: str
    category: str
    difficulty: str
    initial_model_config_id: str
    selected_model_config_id: str
    selected_provider: str
    router_version: str
    escalated: bool
    status: str
    validation_status: str
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
            initial_model_config_id=log.initial_model_config_id,
            selected_model_config_id=log.selected_model_config_id,
            selected_provider=log.selected_provider,
            router_version=log.router_version,
            escalated=log.escalated,
            status=log.status,
            validation_status=log.validation_status,
            latency_ms=log.latency_ms,
            estimated_cost_usd=log.estimated_cost_usd,
            created_at=log.created_at,
        )


class RoutingAnalytics(BaseModel):
    """Live-computed from request_logs — never a fixed snapshot."""

    total_requests: int
    initial_model_counts: dict[str, int]
    final_model_counts: dict[str, int]
    escalation_count: int
    escalation_rate: float | None
    provider_error_count: int
    avg_latency_ms: float | None
    total_cost_usd: float | None
    validation_passed: int
    validation_failed: int
    validation_not_validated: int


class RouterStrategyMetrics(BaseModel):
    """One strategy's row in the router comparison view. Every number
    here is real, measured data from the training manifest — never
    computed on the fly from live traffic (there isn't enough of it yet
    to mean anything), and never estimated.
    """

    strategy: str
    accuracy: float
    correct: int
    n: int
    pct_20b: float
    pct_120b: float
    nominal_cost_usd: float
    avg_latency_ms: float
    # True for every real strategy here (D2 and learned-v2's numbers are
    # both leave-one-out cross-validated, always-20b/120b are just a
    # tautological readout of the same real per-task data) - False only
    # for the oracle, which requires already knowing the answer and is
    # never an implementable strategy.
    is_out_of_sample: bool
    is_theoretical_upper_bound: bool


class RouterComparisonOut(BaseModel):
    """V3 vs D2 vs the single-model baselines vs the oracle ceiling —
    sourced directly from backend/app/routing/learned/artifacts/
    learned-v2.manifest.json (rewritten each time
    scripts/train_router.py runs), not recomputed here.
    """

    evaluation_method: str
    n_evaluated_tasks: int
    trained_at: str
    chosen_algorithm: str
    chosen_algorithm_reason: str
    learned_beats_d2: bool
    learned_beats_always_120b: bool
    strategies: list[RouterStrategyMetrics]
