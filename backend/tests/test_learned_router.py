import pytest

from app.models.enums import ConfidenceLevel, TaskCategory, TaskDifficulty
from app.providers.registry import ModelConfig
from app.routing import learned_router
from app.routing.analyzer import RequestAnalysis
from app.routing.learned.train import LEARNED_ROUTER_VERSION
from app.routing.router import RoutingError


class _FakeModel:
    def __init__(self, predicted_id: str, max_proba: float):
        self._predicted_id = predicted_id
        self._max_proba = max_proba

    def predict(self, X):
        return [self._predicted_id]

    def predict_proba(self, X):
        remainder = (1 - self._max_proba) / 2
        return [[self._max_proba, remainder, remainder]]


@pytest.fixture(autouse=True)
def _reset_model_cache():
    learned_router._MODEL = None
    yield
    learned_router._MODEL = None


def _analysis() -> RequestAnalysis:
    return RequestAnalysis(
        category=TaskCategory.MATH,
        category_source="heuristic",
        difficulty=TaskDifficulty.EASY,
        structured_output_required=False,
        estimated_input_tokens=5,
    )


def _model_lookup(**enabled) -> dict[str, ModelConfig]:
    return {
        model_id: ModelConfig(
            id=model_id,
            provider="mock",
            model_id=model_id,
            display_name=model_id,
            enabled=is_enabled,
            input_cost_per_1k=0.0001,
            output_cost_per_1k=0.0002,
        )
        for model_id, is_enabled in enabled.items()
    }


def test_predicted_model_is_used_when_available(monkeypatch):
    monkeypatch.setattr(learned_router, "_load_model", lambda: _FakeModel("mock-fast-v1", 0.9))
    lookup = _model_lookup(**{"mock-fast-v1": True, "mock-accurate-v1": True})

    decision = learned_router.decide_route_learned(_analysis(), lookup)

    assert decision.selected_model_id == "mock-fast-v1"
    assert decision.router_version == LEARNED_ROUTER_VERSION
    assert decision.confidence == ConfidenceLevel.HIGH
    assert "mock-fast-v1" in decision.rationale


def test_falls_back_to_default_model_when_prediction_is_disabled(monkeypatch):
    monkeypatch.setattr(learned_router, "_load_model", lambda: _FakeModel("mock-fast-v1", 0.6))
    lookup = _model_lookup(**{"mock-fast-v1": False, "mock-accurate-v1": True})

    decision = learned_router.decide_route_learned(_analysis(), lookup)

    assert decision.selected_model_id == "mock-accurate-v1"  # DEFAULT_MODEL_ID
    assert "fall" in decision.rationale.lower()


def test_raises_when_prediction_and_default_are_both_unavailable(monkeypatch):
    monkeypatch.setattr(learned_router, "_load_model", lambda: _FakeModel("mock-fast-v1", 0.6))
    lookup = _model_lookup(**{"mock-fast-v1": False, "mock-accurate-v1": False})

    with pytest.raises(RoutingError):
        learned_router.decide_route_learned(_analysis(), lookup)


def test_confidence_bins_follow_leaf_probability(monkeypatch):
    lookup = _model_lookup(**{"mock-fast-v1": True})

    monkeypatch.setattr(learned_router, "_load_model", lambda: _FakeModel("mock-fast-v1", 0.9))
    assert learned_router.decide_route_learned(_analysis(), lookup).confidence == ConfidenceLevel.HIGH

    monkeypatch.setattr(learned_router, "_load_model", lambda: _FakeModel("mock-fast-v1", 0.6))
    assert learned_router.decide_route_learned(_analysis(), lookup).confidence == ConfidenceLevel.MEDIUM

    monkeypatch.setattr(learned_router, "_load_model", lambda: _FakeModel("mock-fast-v1", 0.4))
    assert learned_router.decide_route_learned(_analysis(), lookup).confidence == ConfidenceLevel.LOW


def test_raises_learned_router_error_without_a_trained_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(learned_router, "ARTIFACT_PATH", tmp_path / "does-not-exist.joblib")
    with pytest.raises(learned_router.LearnedRouterError):
        learned_router.decide_route_learned(_analysis(), _model_lookup(**{"mock-fast-v1": True}))
