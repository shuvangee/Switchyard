"""Routing analytics — every number here is computed live from
request_logs, never a fixed snapshot. If there are no requests yet, counts
are 0 and rates are null, not omitted or estimated.
"""

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import RoutingAnalytics
from app.db.session import get_db
from app.models.enums import ExecutionStatus, ValidationStatus
from app.models.request_log import RequestLogORM

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
