"""FastAPI application entry point.

This is intentionally minimal during project bootstrap: it only exposes a
health check. Routing, provider integration, and evaluation endpoints are
added in later versions (see PROJECT_STATE.md and docs/case-study/).
"""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Switchyard API",
    description="Adaptive multi-model AI routing system — backend service.",
    version="0.0.1",
)

app.include_router(health_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "switchyard-backend", "docs": "/docs"}
