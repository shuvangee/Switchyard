import pytest

from app.core.config import Settings
from app.models.enums import ExecutionStatus, TaskCategory, ValidationStatus
from app.models.request_log import RequestLogORM
from app.providers.base import ProviderError
from app.providers.mock import MockProvider
from app.providers.registry import sync_model_configs
from app.routing.service import MAX_ATTEMPTS, handle_routed_request


def _seed_models(session):
    sync_model_configs(session, Settings(openai_api_key=None))


def test_easy_math_request_routes_to_fast_and_succeeds_no_escalation(db_session):
    _seed_models(db_session)
    log = handle_routed_request(db_session, prompt="What is 17 * 6?")

    assert log.category == TaskCategory.MATH.value
    assert log.category_source == "heuristic"
    assert log.initial_model_config_id == "mock-fast-v1"
    assert log.selected_model_config_id == "mock-fast-v1"
    assert log.selected_provider == "mock"
    assert log.router_version == "v2"
    assert log.status == ExecutionStatus.SUCCESS.value
    assert log.response_text == "102"
    assert log.rationale != ""
    assert log.estimated_cost_usd is not None
    assert log.escalated is False
    assert log.attempt_count == 1
    assert log.validation_status == ValidationStatus.PASSED.value
    assert len(log.trace_events) > 0
    assert log.trace_events[0]["event_type"] == "request_received"
    assert log.trace_events[-1]["event_type"] == "returned"


def test_explicit_category_hint_is_recorded(db_session):
    _seed_models(db_session)
    log = handle_routed_request(
        db_session, prompt="Handle this however you see fit.", category_hint=TaskCategory.CODING
    )
    assert log.category == TaskCategory.CODING.value
    assert log.category_source == "explicit"
    # coding is an unscored category -> conservative default
    assert log.selected_model_config_id == "mock-accurate-v1"


def test_learned_router_version_is_used_when_requested(db_session):
    _seed_models(db_session)
    log = handle_routed_request(db_session, prompt="What is 17 * 6?", router_version="learned-v1")
    assert log.router_version == "learned-v1"
    assert log.selected_model_config_id != ""


def test_always_20b_router_version_ignores_category(db_session):
    _seed_models(db_session)
    log = handle_routed_request(
        db_session, prompt="Summarize this article for me.", router_version="always-20b"
    )
    assert log.router_version == "always-20b"
    assert log.selected_model_config_id == "groq-gpt-oss-20b"


def test_always_120b_router_version_ignores_category(db_session):
    _seed_models(db_session)
    log = handle_routed_request(db_session, prompt="What is 17 * 6?", router_version="always-120b")
    assert log.router_version == "always-120b"
    assert log.selected_model_config_id == "groq-gpt-oss-120b"


def test_d2_baseline_router_version_routes_summarization_to_120b(db_session):
    _seed_models(db_session)
    log = handle_routed_request(
        db_session, prompt="Summarize this article for me.", router_version="d2-baseline"
    )
    assert log.router_version == "d2-baseline"
    assert log.selected_model_config_id == "groq-gpt-oss-120b"
    assert log.router_score is None  # deterministic rule


def test_d2_baseline_router_version_routes_everything_else_to_20b(db_session):
    _seed_models(db_session)
    log = handle_routed_request(db_session, prompt="What is 17 * 6?", router_version="d2-baseline")
    assert log.router_version == "d2-baseline"
    assert log.selected_model_config_id == "groq-gpt-oss-20b"


def test_learned_v2_router_version_is_used_when_requested(db_session):
    _seed_models(db_session)
    log = handle_routed_request(db_session, prompt="What is 17 * 6?", router_version="learned-v2")
    assert log.router_version == "learned-v2"
    assert log.selected_model_config_id in ("groq-gpt-oss-20b", "groq-gpt-oss-120b")
    assert log.router_score is not None  # a trained classifier - always has a real proba
    assert 0.0 <= log.router_score <= 1.0


def test_unknown_router_version_raises(db_session):
    _seed_models(db_session)
    with pytest.raises(ValueError, match="unknown router_version"):
        handle_routed_request(db_session, prompt="What is 17 * 6?", router_version="bogus")


def test_request_is_persisted_and_queryable(db_session):
    _seed_models(db_session)
    log = handle_routed_request(db_session, prompt="What is 2 + 2?")
    fetched = db_session.get(RequestLogORM, log.id)
    assert fetched is not None
    assert fetched.prompt == "What is 2 + 2?"


def test_validation_failure_triggers_escalation_and_fixes_the_actual_v1_bug(db_session):
    """This is the literal V1 failure: "What is -8 + 15?" is estimated
    difficulty=easy by word count and routed to mock-fast-v1, which
    answers 23 (wrong). In V1 that was returned as a silent "success".
    In V2, validation independently computes 7, flags the mismatch,
    escalation kicks in, and mock-accurate-v1 gets it right — no mocking,
    this is the real pipeline end to end.
    """
    _seed_models(db_session)
    log = handle_routed_request(db_session, prompt="What is -8 + 15?")

    assert log.initial_model_config_id == "mock-fast-v1"
    assert log.selected_model_config_id == "mock-accurate-v1"
    assert log.escalated is True
    assert log.attempt_count == 2
    assert log.response_text == "7"
    assert log.validation_status == ValidationStatus.PASSED.value

    event_types = [event["event_type"] for event in log.trace_events]
    assert "escalating" in event_types
    assert event_types.count("model_completed") == 2
    assert event_types.count("validation") == 2


def test_provider_error_triggers_escalation_and_succeeds(db_session, monkeypatch):
    _seed_models(db_session)

    # Force the router's initial pick to mock-flaky-v1 (never a real rule
    # target) so we can deterministically exercise the provider-error ->
    # escalation path without depending on luck.
    from app.models.enums import ConfidenceLevel, TaskDifficulty
    from app.routing.router import RoutingDecision

    forced_decision = RoutingDecision(
        category=TaskCategory.DEBUGGING,
        category_source="explicit",
        difficulty=TaskDifficulty.MEDIUM,
        structured_output_required=False,
        confidence=ConfidenceLevel.HIGH,
        selected_model_id="mock-flaky-v1",
        selected_provider="mock",
        router_version="v2",
        rationale="forced for test",
        matched_rule=None,
    )
    monkeypatch.setattr("app.routing.service.decide_route", lambda analysis, lookup: forced_decision)

    provider = MockProvider()
    flaky_prompt = None
    for i in range(50):
        candidate = f"trigger {i}"
        try:
            provider.generate("mock-flaky-v1", candidate)
        except ProviderError:
            flaky_prompt = candidate
            break
    assert flaky_prompt is not None

    log = handle_routed_request(db_session, prompt=flaky_prompt)

    assert log.initial_model_config_id == "mock-flaky-v1"
    assert log.selected_model_config_id == "mock-accurate-v1"  # escalation target
    assert log.escalated is True
    assert log.attempt_count == 2
    assert log.status == ExecutionStatus.SUCCESS.value  # accurate has 0% error rate
    assert log.response_text is not None

    event_types = [event["event_type"] for event in log.trace_events]
    assert "provider_error" in event_types
    assert "escalating" in event_types


def test_retry_limit_enforced_when_escalated_attempt_also_fails_validation(db_session, monkeypatch):
    """Forces validate_response to always report FAILED, isolating the
    retry-limit/no-infinite-loop guarantee from real validator behavior
    (with the real validators, the escalation target — mock-accurate-v1 —
    is reliable enough on every currently-checkable category that a
    genuine double failure doesn't naturally occur; this proves the bound
    exists regardless).
    """
    _seed_models(db_session)

    from app.evaluation.validation import ValidationOutcome

    monkeypatch.setattr(
        "app.routing.service.validate_response",
        lambda category, prompt, response: ValidationOutcome(ValidationStatus.FAILED, "forced failure"),
    )

    log = handle_routed_request(db_session, prompt="What is 17 * 6?")

    assert log.attempt_count == MAX_ATTEMPTS  # never exceeds the bound
    assert log.escalated is True
    assert log.validation_status == ValidationStatus.FAILED.value
    assert log.status == ExecutionStatus.SUCCESS.value  # the call succeeded; content just never validated
    assert log.response_text is not None  # best-effort response still returned, not discarded

    event_types = [event["event_type"] for event in log.trace_events]
    assert event_types.count("model_completed") == MAX_ATTEMPTS
    assert event_types.count("escalating") == 1  # only one hop: fast has exactly one target
    assert event_types[-1] == "returned"


def test_provider_error_on_escalation_preserves_earlier_completed_response(db_session, monkeypatch):
    """Regression test: a provider error on the escalation attempt used to
    overwrite the only completed response with None, so the request was
    persisted as a bare error even though an earlier attempt had already
    produced a response (it just failed validation). The "return the best
    attempt" contract in this module's docstring requires that earlier
    response to survive.
    """
    _seed_models(db_session)

    from app.evaluation.validation import ValidationOutcome
    from app.providers.base import ProviderResult

    monkeypatch.setattr(
        "app.routing.service.validate_response",
        lambda category, prompt, response: ValidationOutcome(ValidationStatus.FAILED, "forced failure"),
    )

    call_count = {"n": 0}

    def fake_attempt(model, prompt, groq_api_key=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return (
                ProviderResult(text="first attempt answer", input_tokens=10, output_tokens=5, latency_ms=100.0),
                None,
            )
        return None, "escalation target is down"

    monkeypatch.setattr("app.routing.service._attempt", fake_attempt)

    log = handle_routed_request(db_session, prompt="What is 17 * 6?")

    assert log.status == ExecutionStatus.SUCCESS.value  # a real response exists, not a bare error
    assert log.response_text == "first attempt answer"
    assert log.error_message == "escalation target is down"  # kept for context, doesn't hide the response
    assert log.selected_model_config_id == "mock-fast-v1"  # the model that produced the returned response
    assert log.attempt_count == MAX_ATTEMPTS
    assert log.escalated is True
    assert log.latency_ms == 100.0  # only the successful attempt's latency
    assert log.input_tokens == 10
    assert log.output_tokens == 5
    assert log.estimated_cost_usd is not None


def test_cost_and_latency_accumulate_across_a_validation_escalation(db_session, monkeypatch):
    """Regression test: only the FINAL attempt's cost/latency/tokens used
    to be recorded, even when an earlier attempt was also a real, billed
    call — silently dropping its cost from analytics on every validation-
    triggered escalation that ultimately succeeded.
    """
    _seed_models(db_session)

    from app.evaluation.validation import ValidationOutcome
    from app.providers.base import ProviderResult
    from app.providers.pricing import estimate_cost_usd
    from app.providers.registry import get_model_registry

    validation_calls = {"n": 0}

    def fake_validate(category, prompt, response):
        validation_calls["n"] += 1
        status = ValidationStatus.FAILED if validation_calls["n"] == 1 else ValidationStatus.PASSED
        return ValidationOutcome(status, "forced")

    monkeypatch.setattr("app.routing.service.validate_response", fake_validate)

    def fake_attempt(model, prompt, groq_api_key=None):
        if model.id == "mock-fast-v1":
            return ProviderResult(text="wrong", input_tokens=100, output_tokens=50, latency_ms=200.0), None
        return ProviderResult(text="right", input_tokens=80, output_tokens=40, latency_ms=300.0), None

    monkeypatch.setattr("app.routing.service._attempt", fake_attempt)

    log = handle_routed_request(db_session, prompt="What is 17 * 6?")

    assert log.status == ExecutionStatus.SUCCESS.value
    assert log.response_text == "right"  # the response that actually passed validation
    assert log.attempt_count == 2
    assert log.escalated is True
    assert log.input_tokens == 180  # 100 + 80 - both attempts were real, billed calls
    assert log.output_tokens == 90  # 50 + 40
    assert log.latency_ms == 500.0  # 200 + 300

    registry = {m.id: m for m in get_model_registry(Settings(openai_api_key=None))}
    expected_cost = estimate_cost_usd(
        input_cost_per_1k=registry["mock-fast-v1"].input_cost_per_1k,
        output_cost_per_1k=registry["mock-fast-v1"].output_cost_per_1k,
        input_tokens=100,
        output_tokens=50,
    ) + estimate_cost_usd(
        input_cost_per_1k=registry["mock-accurate-v1"].input_cost_per_1k,
        output_cost_per_1k=registry["mock-accurate-v1"].output_cost_per_1k,
        input_tokens=80,
        output_tokens=40,
    )
    assert log.estimated_cost_usd == pytest.approx(expected_cost)


def test_groq_api_key_override_is_threaded_to_the_registry_lookup(db_session, monkeypatch):
    """"Bring your own key": handle_routed_request must pass its
    groq_api_key straight through to get_model_registry's override —
    this is what lets a keyless server still route live for a caller
    who supplies their own key (the enabling behavior itself is proven
    at the registry-unit level in test_provider_registry.py).
    """
    _seed_models(db_session)
    captured: dict[str, str | None] = {}

    def fake_get_model_registry(groq_api_key_override=None):
        captured["override"] = groq_api_key_override
        from app.providers.registry import get_model_registry as real_get_model_registry

        return real_get_model_registry(groq_api_key_override=groq_api_key_override)

    monkeypatch.setattr("app.routing.service.get_model_registry", fake_get_model_registry)

    handle_routed_request(
        db_session,
        prompt="Summarize this article for me.",
        router_version="d2-baseline",
        groq_api_key="user-supplied-key",
    )

    assert captured["override"] == "user-supplied-key"


def test_groq_api_key_override_is_never_persisted_on_the_request_log(db_session):
    _seed_models(db_session)
    log = handle_routed_request(
        db_session,
        prompt="Summarize this article for me.",
        router_version="d2-baseline",
        groq_api_key="a-very-secret-key",
    )
    assert not hasattr(log, "groq_api_key")
    assert "a-very-secret-key" not in (log.rationale or "")
    assert "a-very-secret-key" not in (log.error_message or "")
    assert all("a-very-secret-key" not in event["detail"] for event in log.trace_events)


def test_attempt_only_applies_groq_api_key_override_to_groq_models(monkeypatch):
    from app.providers.registry import ModelConfig
    from app.routing.service import _attempt

    captured: dict[str, str | None] = {}

    def fake_get_provider(name, settings=None, api_key=None):
        captured[name] = api_key
        return MockProvider()

    monkeypatch.setattr("app.routing.service.get_provider", fake_get_provider)

    mock_model = ModelConfig(
        id="mock-accurate-v1",
        provider="mock",
        model_id="mock-accurate-v1",
        display_name="Mock Accurate",
        enabled=True,
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.006,
    )
    _attempt(mock_model, "hello", groq_api_key="a-groq-key-that-must-not-leak-to-mock")

    assert captured["mock"] is None
