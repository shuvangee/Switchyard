"""ORM table for the routing decision + execution record of every request
that goes through the router (Playground submissions today; any future
caller of app/routing/service.py). One row per request — the routing
decision and its resulting execution are 1:1, so they're kept together
rather than split into two joined tables.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RequestLogORM(Base):
    __tablename__ = "request_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    prompt: Mapped[str] = mapped_column(String, nullable=False)

    # --- request analysis ---
    category: Mapped[str] = mapped_column(String, nullable=False)
    category_source: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[str] = mapped_column(String, nullable=False)
    structured_output_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- routing decision ---
    selected_model_config_id: Mapped[str] = mapped_column(String, nullable=False)
    selected_provider: Mapped[str] = mapped_column(String, nullable=False)
    router_version: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(String, nullable=False)
    matched_rule: Mapped[str | None] = mapped_column(String, nullable=True)

    # --- execution result ---
    status: Mapped[str] = mapped_column(String, nullable=False)
    response_text: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
