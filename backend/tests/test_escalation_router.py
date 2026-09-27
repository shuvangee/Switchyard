import pytest

from app.models.enums import ConfidenceLevel, TaskCategory, TaskDifficulty
from app.providers.registry import ModelConfig
from app.routing import escalation_router
from app.routing.analyzer import RequestAnalysis
from app.routing.learned.train_escalation import ESCALATION_ROUTER_VERSION
from app.routing.router import RoutingError


class _FakeModel:
    """classes_ ordered [0, 1] to match how sklearn actually orders
    binary int labels — the real thing this mock stands in for."""

    classes_ = [0, 1]

    def __init__(self, predicted: int, escalate_proba: float):
        self._predicted = predicted
        self._escalate_proba = escalate_proba

    def predict(self, X):
        return [self._predicted]

    def predict_proba(self, X):
        return [[1 - self._escalate_proba, self._escalate_proba]]


@pytest.fixture(autouse=True)
def _reset_model_cache():
    escalation_router._MODEL = None
    yield
    escalation_router._MODEL = None


def _analysis() -> RequestAnalysis:
    return RequestAnalysis(
        category=TaskCategory.SUMMARIZATION,
        category_source="heuristic",
        difficulty=TaskDifficulty.MEDIUM,
        structured_output_required=False,
        estimated_input_tokens=60,
    )


def _model_lookup(**enabled) -> dict[str, ModelConfig]:
    return {
        model_id: ModelConfig(
            id=model_id, provider="groq", model_id=model_id, display_name=model_id,
            enabled=is_enabled, input_cost_per_1k=0.0001, output_cost_per_1k=0.0002,
        )
        for model_id, is_enabled in enabled.items()
    }


def test_predicted_escalate_routes_to_120b(monkeypatch):
    monkeypatch.setattr(escalation_router, "_load_model", lambda: _FakeModel(1, 0.9))
    lookup = _model_lookup(**{"groq-gpt-oss-20b": True, "groq-gpt-oss-120b": True})

    decision = escalation_router.decide_route_escalation(_analysis(), lookup)

    assert decision.selected_model_id == "groq-gpt-oss-120b"
    assert decision.router_version == ESCALATION_ROUTER_VERSION
    assert decision.router_score == pytest.approx(0.9)
    assert decision.confidence == ConfidenceLevel.HIGH
    assert "escalate to 120b" in decision.rationale


def test_predicted_no_escalate_routes_to_20b(monkeypatch):
    monkeypatch.setattr(escalation_router, "_load_model", lambda: _FakeModel(0, 0.1))
    lookup = _model_lookup(**{"groq-gpt-oss-20b": True, "groq-gpt-oss-120b": True})

    decision = escalation_router.decide_route_escalation(_analysis(), lookup)

    assert decision.selected_model_id == "groq-gpt-oss-20b"
    assert decision.router_score == pytest.approx(0.1)
    assert "stay on 20b" in decision.rationale


def test_confidence_bins_follow_distance_from_decision_boundary(monkeypatch):
    lookup = _model_lookup(**{"groq-gpt-oss-20b": True, "groq-gpt-oss-120b": True})

    monkeypatch.setattr(escalation_router, "_load_model", lambda: _FakeModel(1, 0.9))
    assert escalation_router.decide_route_escalation(_analysis(), lookup).confidence == ConfidenceLevel.HIGH

    monkeypatch.setattr(escalation_router, "_load_model", lambda: _FakeModel(1, 0.7))
    assert escalation_router.decide_route_escalation(_analysis(), lookup).confidence == ConfidenceLevel.MEDIUM

    monkeypatch.setattr(escalation_router, "_load_model", lambda: _FakeModel(0, 0.45))
    assert escalation_router.decide_route_escalation(_analysis(), lookup).confidence == ConfidenceLevel.LOW

    # A confident "don't escalate" (low P(escalate)) is also HIGH confidence -
    # confidence is about distance from the boundary, not which side won.
    monkeypatch.setattr(escalation_router, "_load_model", lambda: _FakeModel(0, 0.05))
    assert escalation_router.decide_route_escalation(_analysis(), lookup).confidence == ConfidenceLevel.HIGH


def test_falls_back_to_other_groq_model_when_prediction_disabled(monkeypatch):
    monkeypatch.setattr(escalation_router, "_load_model", lambda: _FakeModel(1, 0.9))
    lookup = _model_lookup(**{"groq-gpt-oss-20b": True, "groq-gpt-oss-120b": False})

    decision = escalation_router.decide_route_escalation(_analysis(), lookup)

    assert decision.selected_model_id == "groq-gpt-oss-20b"
    assert "fallback" in decision.matched_rule


def test_falls_back_to_default_model_when_both_groq_models_unavailable(monkeypatch):
    monkeypatch.setattr(escalation_router, "_load_model", lambda: _FakeModel(1, 0.9))
    lookup = _model_lookup(**{"groq-gpt-oss-20b": False, "groq-gpt-oss-120b": False, "mock-accurate-v1": True})

    decision = escalation_router.decide_route_escalation(_analysis(), lookup)

    assert decision.selected_model_id == "mock-accurate-v1"


def test_raises_when_no_model_available_at_all(monkeypatch):
    monkeypatch.setattr(escalation_router, "_load_model", lambda: _FakeModel(1, 0.9))
    lookup = _model_lookup(**{"groq-gpt-oss-20b": False, "groq-gpt-oss-120b": False})

    with pytest.raises(RoutingError):
        escalation_router.decide_route_escalation(_analysis(), lookup)


def test_raises_escalation_router_error_without_a_trained_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(escalation_router, "ARTIFACT_PATH", tmp_path / "does-not-exist.joblib")
    with pytest.raises(escalation_router.EscalationRouterError):
        escalation_router.decide_route_escalation(_analysis(), _model_lookup(**{"groq-gpt-oss-20b": True}))


def test_raises_escalation_router_error_on_a_corrupt_artifact(tmp_path, monkeypatch):
    corrupt_path = tmp_path / "corrupt.joblib"
    corrupt_path.write_bytes(b"not a real joblib file")
    monkeypatch.setattr(escalation_router, "ARTIFACT_PATH", corrupt_path)
    with pytest.raises(escalation_router.EscalationRouterError):
        escalation_router.decide_route_escalation(_analysis(), _model_lookup(**{"groq-gpt-oss-20b": True}))


def test_predictions_are_deterministic_with_the_real_trained_artifact(tmp_path):
    """Uses the actual training pipeline (not a fake) to produce a real
    artifact, then confirms decide_route_escalation gives byte-identical
    predictions across repeated calls and cache resets - the artifact is
    the single source of truth, not something that drifts per-call."""
    from app.routing.learned.train_escalation import run

    artifact_path = tmp_path / "artifact.joblib"
    run(artifact_path=artifact_path, manifest_path=tmp_path / "manifest.json")

    import app.routing.escalation_router as router_module

    original_artifact_path = router_module.ARTIFACT_PATH
    router_module.ARTIFACT_PATH = artifact_path
    try:
        lookup = _model_lookup(**{"groq-gpt-oss-20b": True, "groq-gpt-oss-120b": True})
        analysis = RequestAnalysis(
            category=TaskCategory.SUMMARIZATION, category_source="explicit",
            difficulty=TaskDifficulty.HARD, structured_output_required=False,
            estimated_input_tokens=200,
        )
        results = []
        for _ in range(3):
            router_module._MODEL = None  # force a fresh load each time
            results.append(router_module.decide_route_escalation(analysis, lookup))
        assert len({d.selected_model_id for d in results}) == 1
        assert len({d.router_score for d in results}) == 1
    finally:
        router_module.ARTIFACT_PATH = original_artifact_path
        router_module._MODEL = None
