"""Ties the analyzer, router, validation, escalation, and persistence
together: the one function the Playground (and any future caller) uses to
route, execute, validate, and — when warranted — retry a request with a
stronger model.

Escalation triggers, each recorded as its own trace event:
- routing confidence was low (handled inside decide_route itself, before
  any model is called — see routing/router.py)
- the provider call raised ProviderError (outage/rate-limit/simulated
  failure)
- the response failed content validation (evaluation/validation.py)

Bounded by MAX_ATTEMPTS so a chain of failures can never loop forever.
Once attempts run out, or a model has no further escalation target, the
best attempt so far is returned — clearly marked as such in the trace and
in validation_status/error_message, never silently presented as a clean
success.
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.evaluation.validation import validate_response
from app.models.enums import ExecutionStatus, TaskCategory, ValidationStatus
from app.models.request_log import RequestLogORM
from app.providers.base import ProviderError, ProviderResult
from app.providers.pricing import estimate_cost_usd
from app.providers.registry import ModelConfig, get_model_registry, get_provider
from app.routing.analyzer import analyze_request
from app.routing.learned.train import LEARNED_ROUTER_VERSION
from app.routing.learned_router import decide_route_learned
from app.routing.router import decide_route
from app.routing.rules import ESCALATION_TARGETS
from app.routing.rules import ROUTER_VERSION as DEFAULT_ROUTER_VERSION
from app.routing.trace import TraceEvent

MAX_ATTEMPTS = 2


def _attempt(model: ModelConfig, prompt: str) -> tuple[ProviderResult | None, str | None]:
    """Returns (result, error_message) — exactly one is None."""
    provider = get_provider(model.provider)
    try:
        return provider.generate(model.model_id, prompt), None
    except ProviderError as exc:
        return None, str(exc)


def _next_escalation_model(
    current_model_id: str, model_lookup: dict[str, ModelConfig], attempts_used: int
) -> str | None:
    if attempts_used >= MAX_ATTEMPTS:
        return None
    next_id = ESCALATION_TARGETS.get(current_model_id)
    if next_id is None:
        return None
    next_model = model_lookup.get(next_id)
    if next_model is None or not next_model.enabled:
        return None
    return next_id


def handle_routed_request(
    session: Session,
    *,
    prompt: str,
    category_hint: TaskCategory | None = None,
    router_version: str | None = None,
) -> RequestLogORM:
    if router_version not in (None, DEFAULT_ROUTER_VERSION, LEARNED_ROUTER_VERSION):
        raise ValueError(
            f"unknown router_version {router_version!r} — expected one of "
            f"{DEFAULT_ROUTER_VERSION!r}, {LEARNED_ROUTER_VERSION!r}, or None"
        )

    analysis = analyze_request(prompt, category_hint=category_hint)
    model_lookup = {model.id: model for model in get_model_registry()}
    if router_version == LEARNED_ROUTER_VERSION:
        decision = decide_route_learned(analysis, model_lookup)
    else:
        decision = decide_route(analysis, model_lookup)

    trace: list[TraceEvent] = [
        TraceEvent.now("request_received", f"prompt received ({len(prompt)} chars)"),
        TraceEvent.now(
            "analyzed",
            f"category={analysis.category.value} ({analysis.category_source}), "
            f"difficulty={analysis.difficulty.value}, "
            f"structured_output_required={analysis.structured_output_required}",
        ),
        TraceEvent.now(
            "routed",
            f"selected {decision.selected_model_id} "
            f"(confidence={decision.confidence.value}, rule={decision.matched_rule or 'default'})",
        ),
    ]

    initial_model_id = decision.selected_model_id
    current_model_id = decision.selected_model_id
    escalated = False
    attempt_count = 0
    result: ProviderResult | None = None
    error_message: str | None = None
    validation_status = ValidationStatus.NOT_VALIDATED
    validation_detail: str | None = None

    # Tracks the most recent attempt that actually produced a response,
    # separately from `result` (which reflects only the LATEST attempt and
    # gets overwritten to None by a subsequent provider error) — otherwise a
    # provider error on the final escalation attempt erases an earlier
    # completed response that the "return the best attempt" contract above
    # promises to keep.
    last_success_result: ProviderResult | None = None
    last_success_model_id: str | None = None

    # Every successful attempt is a real, billed call, even when its
    # response is later superseded by an escalation — accumulated
    # separately from the per-attempt `result` so a validation-triggered
    # escalation doesn't silently drop an earlier attempt's cost/latency
    # from analytics (only the final attempt's numbers were kept before).
    total_latency_ms = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost_usd = 0.0
    metrics_known = True

    while attempt_count < MAX_ATTEMPTS:
        attempt_count += 1
        model = model_lookup[current_model_id]
        result, error_message = _attempt(model, prompt)

        if result is None:
            trace.append(TraceEvent.now("provider_error", f"{current_model_id}: {error_message}"))
            next_model_id = _next_escalation_model(current_model_id, model_lookup, attempt_count)
            if next_model_id is None:
                if last_success_result is not None:
                    trace.append(
                        TraceEvent.now(
                            "returned",
                            "provider error with no further escalation available; "
                            "returning earlier best attempt",
                        )
                    )
                else:
                    trace.append(
                        TraceEvent.now(
                            "returned", "provider error with no further escalation available"
                        )
                    )
                break
            trace.append(TraceEvent.now("escalating", f"provider error -> {next_model_id}"))
            current_model_id = next_model_id
            escalated = True
            continue

        last_success_result = result
        last_success_model_id = current_model_id
        total_latency_ms += result.latency_ms
        if result.input_tokens is None or result.output_tokens is None:
            metrics_known = False
        else:
            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens
        attempt_cost = estimate_cost_usd(
            input_cost_per_1k=model.input_cost_per_1k,
            output_cost_per_1k=model.output_cost_per_1k,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        if attempt_cost is not None:
            total_cost_usd += attempt_cost

        trace.append(TraceEvent.now("model_completed", f"{current_model_id} latency={result.latency_ms:.0f}ms"))
        outcome = validate_response(analysis.category, prompt, result.text)
        validation_status, validation_detail = outcome.status, outcome.detail
        trace.append(TraceEvent.now("validation", f"{outcome.status.value}: {outcome.detail or ''}"))

        if outcome.status != ValidationStatus.FAILED:
            trace.append(TraceEvent.now("returned", "response accepted"))
            break

        next_model_id = _next_escalation_model(current_model_id, model_lookup, attempt_count)
        if next_model_id is None:
            trace.append(
                TraceEvent.now(
                    "returned",
                    "validation failed with no further escalation available; returning best attempt",
                )
            )
            break
        trace.append(TraceEvent.now("escalating", f"validation failed -> {next_model_id}"))
        current_model_id = next_model_id
        escalated = True

    # The response we actually return: the latest attempt if it succeeded,
    # otherwise the last attempt that did (see last_success_result above) —
    # never a bare error when an earlier completed response exists.
    best_result = result if result is not None else last_success_result
    best_model_id = current_model_id if result is not None else last_success_model_id

    if best_result is not None:
        final_model = model_lookup[best_model_id]
        status = ExecutionStatus.SUCCESS.value
        response_text = best_result.text
        latency_ms = total_latency_ms
        if metrics_known:
            input_tokens = total_input_tokens
            output_tokens = total_output_tokens
            cost = total_cost_usd
        else:
            input_tokens = None
            output_tokens = None
            cost = None
    else:
        final_model = model_lookup[current_model_id]
        best_model_id = current_model_id
        status = ExecutionStatus.ERROR.value
        response_text = None
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
        confidence=decision.confidence.value,
        initial_model_config_id=initial_model_id,
        selected_model_config_id=best_model_id,
        selected_provider=final_model.provider,
        router_version=decision.router_version,
        rationale=decision.rationale,
        matched_rule=decision.matched_rule,
        escalated=escalated,
        attempt_count=attempt_count,
        validation_status=validation_status.value,
        validation_detail=validation_detail,
        status=status,
        response_text=response_text,
        error_message=error_message,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
        trace_events=[event.to_dict() for event in trace],
        created_at=utcnow(),
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
