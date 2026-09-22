"""Experiment runner: executes benchmark tasks against models and persists
one ModelExecutionORM row per (task, model) pair.

Execution is synchronous within the calling request/call — reasonable at
V0 scale (a handful of tasks times a handful of models). A background job
queue is not introduced until a version's actual runtime demands it (see
docs/case-study/DECISIONS.md).
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.evaluation.strategies import evaluate
from app.models.benchmark import BenchmarkTaskORM
from app.models.enums import EvaluationStatus, EvaluationType, ExecutionStatus, RunStatus
from app.models.experiment import ExperimentRunORM, ModelExecutionORM
from app.models.model_config import ModelConfigORM
from app.providers.base import ProviderError
from app.providers.pricing import estimate_cost_usd
from app.providers.registry import get_provider


class ExperimentRunnerError(Exception):
    """Raised for invalid run requests (unknown/disabled ids) — never for a
    single model call failing, which is recorded as an error execution
    instead so the rest of the run continues.
    """


def execute_single(task: BenchmarkTaskORM, model: ModelConfigORM) -> ModelExecutionORM:
    provider = get_provider(model.provider)
    started_at = utcnow()

    try:
        result = provider.generate(model.model_id, task.prompt)
    except ProviderError as exc:
        return ModelExecutionORM(
            task_id=task.id,
            model_config_id=model.id,
            status=ExecutionStatus.ERROR.value,
            error_message=str(exc),
            evaluation_status=EvaluationStatus.NOT_EVALUATED.value,
            started_at=started_at,
            completed_at=utcnow(),
        )

    outcome = evaluate(EvaluationType(task.evaluation_type), result.text, task.expected_output)
    cost = estimate_cost_usd(
        input_cost_per_1k=model.input_cost_per_1k,
        output_cost_per_1k=model.output_cost_per_1k,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
    return ModelExecutionORM(
        task_id=task.id,
        model_config_id=model.id,
        status=ExecutionStatus.SUCCESS.value,
        response_text=result.text,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        estimated_cost_usd=cost,
        evaluation_status=outcome.status.value,
        evaluation_detail=outcome.detail,
        started_at=started_at,
        completed_at=utcnow(),
    )


def run_experiment(
    session: Session,
    *,
    task_ids: list[str],
    model_config_ids: list[str],
    name: str | None = None,
) -> ExperimentRunORM:
    if not task_ids:
        raise ExperimentRunnerError("at least one task_id is required")
    if not model_config_ids:
        raise ExperimentRunnerError("at least one model_config_id is required")

    tasks = session.query(BenchmarkTaskORM).filter(BenchmarkTaskORM.id.in_(task_ids)).all()
    missing_tasks = set(task_ids) - {t.id for t in tasks}
    if missing_tasks:
        raise ExperimentRunnerError(f"unknown task ids: {sorted(missing_tasks)}")

    models = session.query(ModelConfigORM).filter(ModelConfigORM.id.in_(model_config_ids)).all()
    missing_models = set(model_config_ids) - {m.id for m in models}
    if missing_models:
        raise ExperimentRunnerError(f"unknown model_config ids: {sorted(missing_models)}")
    disabled = sorted(m.id for m in models if not m.enabled)
    if disabled:
        raise ExperimentRunnerError(f"model_config ids are disabled: {disabled}")

    run = ExperimentRunORM(
        id=str(uuid4()),
        name=name,
        status=RunStatus.RUNNING.value,
        task_ids=task_ids,
        model_config_ids=model_config_ids,
        created_at=utcnow(),
        completed_at=None,
    )
    session.add(run)

    for task in tasks:
        for model in models:
            execution = execute_single(task, model)
            execution.run_id = run.id
            session.add(execution)

    run.status = RunStatus.COMPLETED.value
    run.completed_at = utcnow()
    session.commit()
    session.refresh(run)
    return run
