import pytest

from app.models.enums import TaskCategory, TaskDifficulty
from app.providers.registry import ModelConfig
from app.routing.analyzer import RequestAnalysis
from app.routing.router import RoutingError, decide_route
from app.routing.rules import ROUTER_VERSION


def _model(id_: str, provider: str = "mock", enabled: bool = True) -> ModelConfig:
    return ModelConfig(
        id=id_,
        provider=provider,
        model_id=id_,
        display_name=id_,
        enabled=enabled,
        input_cost_per_1k=0.0001,
        output_cost_per_1k=0.0002,
    )


FULL_REGISTRY = {
    "mock-fast-v1": _model("mock-fast-v1"),
    "mock-accurate-v1": _model("mock-accurate-v1"),
    "mock-flaky-v1": _model("mock-flaky-v1"),
}


def _analysis(category: TaskCategory, difficulty: TaskDifficulty, structured: bool = False) -> RequestAnalysis:
    return RequestAnalysis(
        category=category,
        category_source="explicit",
        difficulty=difficulty,
        structured_output_required=structured,
        estimated_input_tokens=10,
    )


def test_easy_math_routes_to_fast_with_rationale_and_rule_name():
    decision = decide_route(_analysis(TaskCategory.MATH, TaskDifficulty.EASY), FULL_REGISTRY)
    assert decision.selected_model_id == "mock-fast-v1"
    assert decision.selected_provider == "mock"
    assert decision.router_version == ROUTER_VERSION
    assert decision.matched_rule == "easy-deterministic-to-fast"
    assert "V0 baseline" in decision.rationale


def test_hard_math_routes_to_accurate():
    decision = decide_route(_analysis(TaskCategory.MATH, TaskDifficulty.HARD), FULL_REGISTRY)
    assert decision.selected_model_id == "mock-accurate-v1"


def test_coding_routes_to_accurate_regardless_of_difficulty():
    decision = decide_route(_analysis(TaskCategory.CODING, TaskDifficulty.EASY), FULL_REGISTRY)
    assert decision.selected_model_id == "mock-accurate-v1"
    assert decision.matched_rule == "unscored-category-conservative-default"


def test_disabled_target_model_falls_through_to_next_rule_or_default():
    registry = dict(FULL_REGISTRY)
    registry["mock-fast-v1"] = _model("mock-fast-v1", enabled=False)
    decision = decide_route(_analysis(TaskCategory.MATH, TaskDifficulty.EASY), registry)
    # easy-deterministic-to-fast's target is disabled, so it should not match;
    # no other rule targets mock-fast-v1 for this case, so it falls to default.
    assert decision.selected_model_id == "mock-accurate-v1"
    assert decision.matched_rule is None


def test_no_available_model_raises_routing_error():
    registry = {
        "mock-fast-v1": _model("mock-fast-v1", enabled=False),
        "mock-accurate-v1": _model("mock-accurate-v1", enabled=False),
        "mock-flaky-v1": _model("mock-flaky-v1", enabled=False),
    }
    with pytest.raises(RoutingError):
        decide_route(_analysis(TaskCategory.MATH, TaskDifficulty.EASY), registry)


def test_decision_carries_analysis_fields_through():
    analysis = _analysis(TaskCategory.STRUCTURED_OUTPUT, TaskDifficulty.MEDIUM, structured=True)
    decision = decide_route(analysis, FULL_REGISTRY)
    assert decision.category == TaskCategory.STRUCTURED_OUTPUT
    assert decision.difficulty == TaskDifficulty.MEDIUM
    assert decision.structured_output_required is True
    assert decision.category_source == "explicit"
