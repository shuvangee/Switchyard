from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import BenchmarkTaskOut
from app.db.session import get_db
from app.models.benchmark import BenchmarkTaskORM
from app.models.enums import TaskCategory, TaskDifficulty

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("", response_model=list[BenchmarkTaskOut])
def list_benchmarks(
    category: TaskCategory | None = None,
    difficulty: TaskDifficulty | None = None,
    db: Session = Depends(get_db),
) -> list[BenchmarkTaskOut]:
    query = db.query(BenchmarkTaskORM)
    if category is not None:
        query = query.filter(BenchmarkTaskORM.category == category.value)
    if difficulty is not None:
        query = query.filter(BenchmarkTaskORM.difficulty == difficulty.value)
    tasks = query.order_by(BenchmarkTaskORM.id).all()
    return [BenchmarkTaskOut.from_orm_task(task) for task in tasks]


@router.get("/{task_id}", response_model=BenchmarkTaskOut)
def get_benchmark(task_id: str, db: Session = Depends(get_db)) -> BenchmarkTaskOut:
    task = db.get(BenchmarkTaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"benchmark task {task_id!r} not found")
    return BenchmarkTaskOut.from_orm_task(task)
