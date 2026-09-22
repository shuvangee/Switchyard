"""FastAPI application entry point.

On startup, tables are created and the benchmark task files + model
registry are synced into the database so the API always reflects what is
currently on disk/in code.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.benchmarks import router as benchmarks_router
from app.api.experiments import router as experiments_router
from app.api.health import router as health_router
from app.api.model_configs import router as model_configs_router
from app.api.routing import router as routing_router
from app.core.config import get_settings
from app.db.init_db import init_db
from app.db.session import SessionLocal, engine
from app.experiments.loader import get_benchmarks_dir, load_benchmark_tasks, sync_benchmark_tasks
from app.providers.registry import sync_model_configs

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db(engine)
    session = SessionLocal()
    try:
        tasks = load_benchmark_tasks(get_benchmarks_dir(settings))
        sync_benchmark_tasks(session, tasks)
        sync_model_configs(session, settings)
    finally:
        session.close()
    yield


app = FastAPI(
    title="Switchyard API",
    description="Adaptive multi-model AI routing system — backend service.",
    version="0.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(benchmarks_router)
app.include_router(model_configs_router)
app.include_router(experiments_router)
app.include_router(routing_router)
app.include_router(analytics_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "switchyard-backend", "docs": "/docs"}
