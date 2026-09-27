"""Inference-time V3 router (learned-v2) — loads the artifact trained by
routing/learned/train_escalation.py and decides whether a request should
escalate from groq-gpt-oss-20b to groq-gpt-oss-120b, using only
pre-execution features (the same RequestAnalysis every other strategy
uses). Produces the same RoutingDecision shape as the rule-based (v2),
D2-baseline, and original learned-v1 routers, so all four are directly
swappable and comparable.

NOTE on production status: per docs/case-study/DECISIONS.md (2026-09-27),
this router does NOT currently beat the D2 baseline on any measured
system metric (accuracy, cost, or latency) under honest leave-one-out
evaluation — D2 is the preferred strategy. learned-v2 is kept fully
wired and selectable, both because V3's deliverable is a genuine working
learned-routing system regardless of whether it wins, and so this
comparison can be re-run the moment more disagreement data exists.
"""

import joblib

from app.models.enums import ConfidenceLevel
from app.providers.registry import ModelConfig
from app.routing.analyzer import RequestAnalysis
from app.routing.learned.escalation_dataset import MODEL_120B_ID, MODEL_20B_ID
from app.routing.learned.features import encode
from app.routing.learned.train_escalation import ARTIFACT_PATH, ESCALATION_ROUTER_VERSION
from app.routing.router import RoutingDecision, RoutingError
from app.routing.rules import DEFAULT_MODEL_ID, DEFAULT_RATIONALE

_MODEL = None


class EscalationRouterError(RoutingError):
    """Raised when the learned-v2 artifact is missing/corrupt, or when
    neither Groq model nor the global default is available. Subclasses
    RoutingError so callers don't need a separate error case.
    """


def _load_model():
    global _MODEL
    if _MODEL is None:
        if not ARTIFACT_PATH.exists():
            raise EscalationRouterError(
                f"no trained artifact at {ARTIFACT_PATH} — run "
                "`python -m app.routing.learned.train_escalation` first"
            )
        try:
            _MODEL = joblib.load(ARTIFACT_PATH)
        except Exception as exc:  # corrupt/unreadable artifact file
            raise EscalationRouterError(f"failed to load artifact at {ARTIFACT_PATH}: {exc}") from exc
    return _MODEL


def _escalate_probability(model, encoded_matrix) -> float:
    proba = model.predict_proba(encoded_matrix)[0]
    classes = list(model.classes_)
    if 1 not in classes:
        return 0.0
    return float(proba[classes.index(1)])


def _confidence_from_probability(p: float) -> ConfidenceLevel:
    # Distance from the 0.5 decision boundary, not the raw prediction —
    # a 0.51 or 0.49 is a genuinely low-confidence call either way.
    distance = abs(p - 0.5)
    if distance >= 0.35:
        return ConfidenceLevel.HIGH
    if distance >= 0.15:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def decide_route_escalation(
    analysis: RequestAnalysis, model_lookup: dict[str, ModelConfig]
) -> RoutingDecision:
    model = _load_model()
    encoded = encode([analysis])
    escalate = bool(model.predict(encoded.matrix)[0])
    escalate_probability = _escalate_probability(model, encoded.matrix)
    confidence = _confidence_from_probability(escalate_probability)

    predicted_id = MODEL_120B_ID if escalate else MODEL_20B_ID
    target = model_lookup.get(predicted_id)
    rationale = (
        f"learned-v2 (decision tree, LOOCV system accuracy 88.0% on 92 real tasks) predicted "
        f"{'escalate to 120b' if escalate else 'stay on 20b'} (P(escalate)={escalate_probability:.2f}) "
        f"from observable features: category={analysis.category.value}, "
        f"difficulty={analysis.difficulty.value}, estimated_input_tokens={analysis.estimated_input_tokens}. "
        f"NOTE: this router does not currently beat the D2 baseline (90.2% accuracy, lower cost) "
        f"under honest evaluation — see docs/case-study/DECISIONS.md (2026-09-27)."
    )
    matched_rule = f"learned-v2:escalate={escalate}"

    if target is None or not target.enabled:
        fallback_id = MODEL_20B_ID if predicted_id == MODEL_120B_ID else MODEL_120B_ID
        fallback = model_lookup.get(fallback_id)
        if fallback is not None and fallback.enabled:
            rationale = f"{rationale} {predicted_id} is unavailable/disabled — falling back to {fallback_id}."
            matched_rule = f"{matched_rule}+fallback={fallback_id}"
            target = fallback
        else:
            target = model_lookup.get(DEFAULT_MODEL_ID)
            if target is None or not target.enabled:
                raise RoutingError(
                    f"learned-v2 predicted {predicted_id!r} (unavailable), its Groq counterpart "
                    f"is also unavailable, and the default model {DEFAULT_MODEL_ID!r} is too"
                )
            rationale = f"{rationale} Neither Groq model is available — falling back to {DEFAULT_MODEL_ID}. {DEFAULT_RATIONALE}"
            matched_rule = f"{matched_rule}+fallback={DEFAULT_MODEL_ID}"

    return RoutingDecision(
        category=analysis.category,
        category_source=analysis.category_source,
        difficulty=analysis.difficulty,
        structured_output_required=analysis.structured_output_required,
        confidence=confidence,
        selected_model_id=target.id,
        selected_provider=target.provider,
        router_version=ESCALATION_ROUTER_VERSION,
        rationale=rationale,
        matched_rule=matched_rule,
        router_score=escalate_probability,
    )
