"""Routing analytics — every number here is computed live from
request_logs, never a fixed snapshot. If there are no requests yet, counts
are 0 and rates are null, not omitted or estimated.

router-comparison is the one exception to "computed live": there isn't
enough real Playground traffic yet for a live strategy comparison to
mean anything, so it reads the real offline training manifest instead
(backend/app/routing/learned/artifacts/learned-v2.manifest.json) —
still real, measured data (leave-one-out cross-validated against the
92 real Groq-graded tasks), just not computed per-request.
"""

import json
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import RouterComparisonOut, RouterStrategyMetrics, RoutingAnalytics
from app.db.session import get_db
from app.models.enums import ExecutionStatus, ValidationStatus
from app.models.request_log import RequestLogORM
from app.routing.learned.train_escalation import MANIFEST_PATH

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=RoutingAnalytics)
def get_analytics(db: Session = Depends(get_db)) -> RoutingAnalytics:
    logs = db.query(RequestLogORM).all()
    total = len(logs)

    if total == 0:
        return RoutingAnalytics(
            total_requests=0,
            initial_model_counts={},
            final_model_counts={},
            escalation_count=0,
            escalation_rate=None,
            provider_error_count=0,
            avg_latency_ms=None,
            total_cost_usd=None,
            validation_passed=0,
            validation_failed=0,
            validation_not_validated=0,
        )

    initial_counts = Counter(log.initial_model_config_id for log in logs)
    final_counts = Counter(log.selected_model_config_id for log in logs)
    escalation_count = sum(1 for log in logs if log.escalated)
    provider_error_count = sum(1 for log in logs if log.status == ExecutionStatus.ERROR.value)
    latencies = [log.latency_ms for log in logs if log.latency_ms is not None]
    costs = [log.estimated_cost_usd for log in logs if log.estimated_cost_usd is not None]

    return RoutingAnalytics(
        total_requests=total,
        initial_model_counts=dict(initial_counts),
        final_model_counts=dict(final_counts),
        escalation_count=escalation_count,
        escalation_rate=escalation_count / total,
        provider_error_count=provider_error_count,
        avg_latency_ms=(sum(latencies) / len(latencies)) if latencies else None,
        total_cost_usd=sum(costs) if costs else None,
        validation_passed=sum(1 for log in logs if log.validation_status == ValidationStatus.PASSED.value),
        validation_failed=sum(1 for log in logs if log.validation_status == ValidationStatus.FAILED.value),
        validation_not_validated=sum(
            1 for log in logs if log.validation_status == ValidationStatus.NOT_VALIDATED.value
        ),
    )


def _strategy_row(name: str, metrics: dict, *, out_of_sample: bool, theoretical: bool = False) -> RouterStrategyMetrics:
    return RouterStrategyMetrics(
        strategy=name,
        accuracy=metrics["accuracy"],
        correct=metrics["correct"],
        n=metrics["n"],
        pct_20b=1.0 - metrics["pct_120b"],
        pct_120b=metrics["pct_120b"],
        nominal_cost_usd=metrics["nominal_cost_usd"],
        avg_latency_ms=metrics["avg_latency_ms"],
        is_out_of_sample=out_of_sample,
        is_theoretical_upper_bound=theoretical,
    )


@router.get("/router-comparison", response_model=RouterComparisonOut)
def get_router_comparison() -> RouterComparisonOut:
    if not MANIFEST_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=f"no training manifest at {MANIFEST_PATH} — run `python scripts/train_router.py` first",
        )
    manifest = json.loads(MANIFEST_PATH.read_text())
    baselines = manifest["baselines_same_92_rows"]

    strategies = [
        _strategy_row("always-20b", baselines["always-20b"], out_of_sample=True),
        _strategy_row("always-120b", baselines["always-120b"], out_of_sample=True),
        _strategy_row("d2-baseline", baselines["d2-baseline"], out_of_sample=True),
        _strategy_row(
            f"learned-v2 ({manifest['chosen_algorithm']})",
            manifest["learned_router_system_metrics_loocv"],
            out_of_sample=True,
        ),
        _strategy_row("oracle", baselines["oracle"], out_of_sample=False, theoretical=True),
    ]

    return RouterComparisonOut(
        evaluation_method=manifest["evaluation_method"],
        n_evaluated_tasks=manifest["n_training_rows"],
        trained_at=manifest["trained_at"],
        chosen_algorithm=manifest["chosen_algorithm"],
        chosen_algorithm_reason=manifest["chosen_algorithm_reason"],
        learned_beats_d2=manifest["learned_beats_d2"],
        learned_beats_always_120b=manifest["learned_beats_always_120b"],
        strategies=strategies,
    )
