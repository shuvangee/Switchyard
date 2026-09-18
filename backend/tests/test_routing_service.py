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
