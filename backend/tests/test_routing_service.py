from app.core.config import Settings
from app.models.enums import ExecutionStatus, TaskCategory, TaskDifficulty
from app.models.request_log import RequestLogORM
from app.providers.base import ProviderError
from app.providers.mock import MockProvider
from app.providers.registry import sync_model_configs
from app.routing.router import RoutingDecision
from app.routing.rules import ROUTER_VERSION
from app.routing.service import handle_routed_request


def _seed_models(session):
    sync_model_configs(session, Settings(openai_api_key=None))


def test_easy_math_request_routes_to_fast_and_succeeds(db_session):
    _seed_models(db_session)
    log = handle_routed_request(db_session, prompt="What is 17 * 6?")

    assert log.category == TaskCategory.MATH.value
    assert log.category_source == "heuristic"
    assert log.selected_model_config_id == "mock-fast-v1"
    assert log.selected_provider == "mock"
    assert log.router_version == "v1"
    assert log.status == ExecutionStatus.SUCCESS.value
    assert log.response_text == "102"
    assert log.rationale != ""
    assert log.estimated_cost_usd is not None


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


def test_provider_error_still_records_full_routing_decision(db_session, monkeypatch):
    _seed_models(db_session)

    # mock-flaky-v1 is never a routing target under the real rules (nothing
    # in the V0 evidence justifies it), so the only way to exercise the
    # service's error-handling path is to force the router's decision for
    # this test — isolating "does handle_routed_request record correctly
    # on failure" from "which model do the rules pick."
    forced_decision = RoutingDecision(
        category=TaskCategory.DEBUGGING,
        category_source="explicit",
        difficulty=TaskDifficulty.MEDIUM,
        structured_output_required=False,
        selected_model_id="mock-flaky-v1",
        selected_provider="mock",
        router_version=ROUTER_VERSION,
        rationale="forced for test",
        matched_rule=None,
    )
    monkeypatch.setattr(
        "app.routing.service.decide_route", lambda analysis, lookup: forced_decision
    )

    # find a prompt that deterministically trips mock-flaky-v1's simulated
    # error, so this test doesn't depend on luck.
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

    assert log.selected_model_config_id == "mock-flaky-v1"
    assert log.status == ExecutionStatus.ERROR.value
    assert log.response_text is None
    assert log.error_message is not None
    assert log.estimated_cost_usd is None
    # the routing decision itself is still fully recorded despite the failure
    assert log.category == TaskCategory.DEBUGGING.value
    assert log.rationale == "forced for test"
