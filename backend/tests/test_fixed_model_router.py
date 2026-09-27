import pytest

from app.models.enums import TaskCategory, TaskDifficulty
from app.providers.registry import ModelConfig
from app.routing.analyzer import RequestAnalysis
from app.routing.fixed_model_router import (
    ALWAYS_20B_ROUTER_VERSION,
    ALWAYS_120B_ROUTER_VERSION,
    decide_route_fixed,
)
from app.routing.router import RoutingError


def _model(id_: str, enabled: bool = True) -> ModelConfig:
    return ModelConfig(
        id=id_, provider="groq", model_id=id_, display_name=id_,
        enabled=enabled, input_cost_per_1k=0.0001, output_cost_per_1k=0.0002,
    )


FULL_REGISTRY = {
    "groq-gpt-oss-20b": _model("groq-gpt-oss-20b"),
    "groq-gpt-oss-120b": _model("groq-gpt-oss-120b"),
}


def _analysis(category: TaskCategory = TaskCategory.MATH) -> RequestAnalysis:
    return RequestAnalysis(
        category=category, category_source="explicit", difficulty=TaskDifficulty.MEDIUM,
        structured_output_required=False, estimated_input_tokens=40,
    )


@pytest.mark.parametrize(
    "router_version,expected_model",
    [(ALWAYS_20B_ROUTER_VERSION, "groq-gpt-oss-20b"), (ALWAYS_120B_ROUTER_VERSION, "groq-gpt-oss-120b")],
)
def test_always_routes_to_its_fixed_model_regardless_of_category(router_version, expected_model):
    for category in TaskCategory:
        decision = decide_route_fixed(router_version, _analysis(category), FULL_REGISTRY)
        assert decision.selected_model_id == expected_model, category
        assert decision.router_version == router_version
        assert decision.router_score is None


def test_always_20b_falls_back_to_default_when_unavailable():
    registry = {
        "groq-gpt-oss-20b": _model("groq-gpt-oss-20b", enabled=False),
        "mock-accurate-v1": _model("mock-accurate-v1"),
    }
    decision = decide_route_fixed(ALWAYS_20B_ROUTER_VERSION, _analysis(), registry)
    assert decision.selected_model_id == "mock-accurate-v1"
    assert "fallback" in decision.matched_rule


def test_always_120b_raises_when_no_model_available():
    registry = {"groq-gpt-oss-120b": _model("groq-gpt-oss-120b", enabled=False)}
    with pytest.raises(RoutingError):
        decide_route_fixed(ALWAYS_120B_ROUTER_VERSION, _analysis(), registry)
