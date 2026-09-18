"""Ties the analyzer, router, a provider, and persistence together: the
one function the Playground (and any future caller) uses to actually
route and execute a request.
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.enums import ExecutionStatus, TaskCategory
from app.models.request_log import RequestLogORM
from app.providers.base import ProviderError
from app.providers.pricing import estimate_cost_usd
from app.providers.registry import get_model_registry, get_provider
from app.routing.analyzer import analyze_request
from app.routing.router import decide_route


def handle_routed_request(
    session: Session, *, prompt: str, category_hint: TaskCategory | None = None
) -> RequestLogORM:
    analysis = analyze_request(prompt, category_hint=category_hint)
    model_lookup = {model.id: model for model in get_model_registry()}
    decision = decide_route(analysis, model_lookup)
    selected_model = model_lookup[decision.selected_model_id]

    provider = get_provider(decision.selected_provider)
    try:
        result = provider.generate(selected_model.model_id, prompt)
        status = ExecutionStatus.SUCCESS.value
        response_text = result.text
        error_message = None
        latency_ms = result.latency_ms
        input_tokens = result.input_tokens
        output_tokens = result.output_tokens
        cost = estimate_cost_usd(
            input_cost_per_1k=selected_model.input_cost_per_1k,
            output_cost_per_1k=selected_model.output_cost_per_1k,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except ProviderError as exc:
        status = ExecutionStatus.ERROR.value
        response_text = None
        error_message = str(exc)
        latency_ms = None
        input_tokens = None
        output_tokens = None
        cost = None

    log = RequestLogORM(
        id=str(uuid4()),
        prompt=prompt,
        category=decision.category.value,
        category_source=decision.category_source,
        difficulty=decision.difficulty.value,
        structured_output_required=decision.structured_output_required,
        estimated_input_tokens=analysis.estimated_input_tokens,
        selected_model_config_id=decision.selected_model_id,
        selected_provider=decision.selected_provider,
        router_version=decision.router_version,
        rationale=decision.rationale,
        matched_rule=decision.matched_rule,
        status=status,
        response_text=response_text,
        error_message=error_message,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
        created_at=utcnow(),
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
