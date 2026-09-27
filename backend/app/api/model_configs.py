from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import BenchmarkPerformanceSummary, ModelConfigOut, ModelPerformanceSummary
from app.db.session import get_db
from app.experiments.results_reader import model_benchmark_performance
from app.models.enums import EvaluationStatus
from app.models.experiment import ModelExecutionORM
from app.models.model_config import ModelConfigORM

router = APIRouter(prefix="/models", tags=["models"])


def _benchmark_performance(model_id: str) -> BenchmarkPerformanceSummary | None:
    result = model_benchmark_performance(model_id)
    if result is None:
        return None
    return BenchmarkPerformanceSummary(**result)


def _performance_summary(db: Session, model_id: str) -> ModelPerformanceSummary | None:
    executions = (
        db.query(ModelExecutionORM).filter(ModelExecutionORM.model_config_id == model_id).all()
    )
    if not executions:
        return None

    scored = [e for e in executions if e.evaluation_status != EvaluationStatus.NOT_EVALUATED.value]
    correct = sum(1 for e in scored if e.evaluation_status == EvaluationStatus.CORRECT.value)
    latencies = [e.latency_ms for e in executions if e.latency_ms is not None]
    costs = [e.estimated_cost_usd for e in executions if e.estimated_cost_usd is not None]

    return ModelPerformanceSummary(
        total_executions=len(executions),
        scored_executions=len(scored),
        correct=correct,
        avg_latency_ms=(sum(latencies) / len(latencies)) if latencies else None,
        total_cost_usd=sum(costs) if costs else None,
    )


@router.get("", response_model=list[ModelConfigOut])
def list_models(db: Session = Depends(get_db)) -> list[ModelConfigOut]:
    models = db.query(ModelConfigORM).order_by(ModelConfigORM.id).all()
    return [
        ModelConfigOut.from_orm_model(
            model,
            performance=_performance_summary(db, model.id),
            benchmark_performance=_benchmark_performance(model.id),
        )
        for model in models
    ]
