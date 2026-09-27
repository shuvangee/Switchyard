import pytest

from app.models.enums import TaskCategory, TaskDifficulty
from app.providers.registry import ModelConfig
from app.routing.analyzer import RequestAnalysis
from app.routing.d2_router import D2_ROUTER_VERSION, decide_route_d2
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


def _analysis(category: TaskCategory) -> RequestAnalysis:
    return RequestAnalysis(
        category=category, category_source="explicit", difficulty=TaskDifficulty.MEDIUM,
        structured_output_required=False, estimated_input_tokens=40,
    )


def test_summarization_routes_to_120b():
    decision = decide_route_d2(_analysis(TaskCategory.SUMMARIZATION), FULL_REGISTRY)
    assert decision.selected_model_id == "groq-gpt-oss-120b"
    assert decision.router_version == D2_ROUTER_VERSION
    assert decision.matched_rule == "d2-summarization-override"
    assert decision.router_score is None  # deterministic rule, no real score to report


def test_every_other_category_routes_to_20b():
    for category in TaskCategory:
        if category == TaskCategory.SUMMARIZATION:
            continue
        decision = decide_route_d2(_analysis(category), FULL_REGISTRY)
        assert decision.selected_model_id == "groq-gpt-oss-20b", category


def test_disabled_120b_falls_back_to_20b():
    registry = {"groq-gpt-oss-20b": _model("groq-gpt-oss-20b"), "groq-gpt-oss-120b": _model("groq-gpt-oss-120b", enabled=False)}
    decision = decide_route_d2(_analysis(TaskCategory.SUMMARIZATION), registry)
    assert decision.selected_model_id == "groq-gpt-oss-20b"
    assert "fallback" in decision.matched_rule


def test_both_groq_models_unavailable_falls_back_to_default():
    registry = {
        "groq-gpt-oss-20b": _model("groq-gpt-oss-20b", enabled=False),
        "groq-gpt-oss-120b": _model("groq-gpt-oss-120b", enabled=False),
        "mock-accurate-v1": _model("mock-accurate-v1"),
    }
    decision = decide_route_d2(_analysis(TaskCategory.SUMMARIZATION), registry)
    assert decision.selected_model_id == "mock-accurate-v1"
    assert "fallback=mock-accurate-v1" in decision.matched_rule


def test_no_model_available_at_all_raises():
    registry = {
        "groq-gpt-oss-20b": _model("groq-gpt-oss-20b", enabled=False),
        "groq-gpt-oss-120b": _model("groq-gpt-oss-120b", enabled=False),
    }
    with pytest.raises(RoutingError):
        decide_route_d2(_analysis(TaskCategory.SUMMARIZATION), registry)


def test_decision_carries_analysis_fields_through():
    analysis = _analysis(TaskCategory.MATH)
    decision = decide_route_d2(analysis, FULL_REGISTRY)
    assert decision.category == TaskCategory.MATH
    assert decision.difficulty == TaskDifficulty.MEDIUM
