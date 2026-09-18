from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import (
    CreateExperimentRequest,
    ExperimentRunDetail,
    ExperimentRunSummary,
    ModelExecutionOut,
)
from app.db.session import get_db
from app.experiments.runner import ExperimentRunnerError, run_experiment
from app.models.benchmark import BenchmarkTaskORM
from app.models.experiment import ExperimentRunORM
from app.models.model_config import ModelConfigORM

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentRunSummary])
def list_experiments(db: Session = Depends(get_db)) -> list[ExperimentRunSummary]:
    runs = db.query(ExperimentRunORM).order_by(ExperimentRunORM.created_at.desc()).all()
    return [
        ExperimentRunSummary(
            id=run.id,
            name=run.name,
            status=run.status,
            task_count=len(run.task_ids),
            model_count=len(run.model_config_ids),
            execution_count=len(run.executions),
            created_at=run.created_at,
            completed_at=run.completed_at,
        )
        for run in runs
    ]


@router.post("", response_model=ExperimentRunDetail, status_code=201)
def create_experiment(
    payload: CreateExperimentRequest, db: Session = Depends(get_db)
) -> ExperimentRunDetail:
    if payload.task_ids:
        task_ids = payload.task_ids
    elif payload.category is not None:
        task_ids = [
            task.id
            for task in db.query(BenchmarkTaskORM)
            .filter(BenchmarkTaskORM.category == payload.category.value)
            .all()
        ]
        if not task_ids:
            raise HTTPException(
                status_code=400,
                detail=f"no benchmark tasks found for category {payload.category.value!r}",
            )
    else:
        raise HTTPException(status_code=400, detail="must provide either task_ids or category")

    try:
        run = run_experiment(
            db, task_ids=task_ids, model_config_ids=payload.model_config_ids, name=payload.name
        )
    except ExperimentRunnerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _build_run_detail(db, run)


@router.get("/{run_id}", response_model=ExperimentRunDetail)
def get_experiment(run_id: str, db: Session = Depends(get_db)) -> ExperimentRunDetail:
    run = db.get(ExperimentRunORM, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"experiment run {run_id!r} not found")
    return _build_run_detail(db, run)


def _build_run_detail(db: Session, run: ExperimentRunORM) -> ExperimentRunDetail:
    models_by_id = {model.id: model for model in db.query(ModelConfigORM).all()}
    executions = [
        ModelExecutionOut.from_orm_execution(
            execution,
            provider=models_by_id[execution.model_config_id].provider
            if execution.model_config_id in models_by_id
            else "unknown",
        )
        for execution in run.executions
    ]
    return ExperimentRunDetail(
        id=run.id,
        name=run.name,
        status=run.status,
        task_ids=run.task_ids,
        model_config_ids=run.model_config_ids,
        created_at=run.created_at,
        completed_at=run.completed_at,
        executions=executions,
    )
