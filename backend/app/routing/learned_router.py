"""Inference-time learned router (V3) — loads the artifact trained by
routing/learned/train.py and produces the same RoutingDecision shape V1's
rule-based router does, so the two are swappable behind one interface.

See docs/case-study/EXPERIMENTS.md (2026-09-22) before using this for
anything real: on leave-one-out evaluation against the only data that
exists, this router is strictly dominated by the trivial always-cheapest
baseline (worse accuracy, higher cost) and loses to V1's rules and even
random selection. It is wired up and functional, not recommended.
"""

import joblib

from app.models.enums import ConfidenceLevel
from app.providers.registry import ModelConfig
from app.routing.analyzer import RequestAnalysis
from app.routing.learned.features import encode
from app.routing.learned.train import ARTIFACT_PATH, LEARNED_ROUTER_VERSION
from app.routing.router import RoutingDecision, RoutingError
from app.routing.rules import DEFAULT_MODEL_ID, DEFAULT_RATIONALE

_MODEL = None


class LearnedRouterError(RoutingError):
    """Raised when the learned router artifact doesn't exist or can't be used.

    Subclasses RoutingError so API/service error handling doesn't need a
    separate case for "learned router isn't available" vs. "no rule
    matched" — both mean the same thing to a caller: routing failed.
    """


def _load_model():
    global _MODEL
    if _MODEL is None:
        if not ARTIFACT_PATH.exists():
            raise LearnedRouterError(
                f"no trained artifact at {ARTIFACT_PATH} — run "
                "`python -m app.routing.learned.train` first"
            )
        _MODEL = joblib.load(ARTIFACT_PATH)
    return _MODEL


def _confidence_from_proba(max_proba: float) -> ConfidenceLevel:
    """A leaf's predict_proba is the fraction of ITS training examples
    that were this class — a real signal, but from 24 rows total and a
    depth-2 tree, not a calibrated probability. Same caveat as V1's
    heuristic confidence (see router.py:estimate_confidence).
    """
    if max_proba >= 0.75:
        return ConfidenceLevel.HIGH
    if max_proba >= 0.5:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def decide_route_learned(
    analysis: RequestAnalysis, model_lookup: dict[str, ModelConfig]
) -> RoutingDecision:
    model = _load_model()
    encoded = encode([analysis])
    predicted_id = model.predict(encoded.matrix)[0]
    proba = model.predict_proba(encoded.matrix)[0]
    max_proba = float(max(proba))
    confidence = _confidence_from_proba(max_proba)

    target = model_lookup.get(predicted_id)
    if target is not None and target.enabled:
        rationale = (
            f"learned-v1 (decision tree, trained on 24 real task outcomes) predicted "
            f"{predicted_id} with leaf confidence {max_proba:.2f}. NOTE: this router is "
            f"NOT recommended for real use — leave-one-out evaluation showed it is "
            f"dominated by the trivial always-cheapest baseline. See "
            f"docs/case-study/EXPERIMENTS.md (2026-09-22)."
        )
        matched_rule = f"learned-v1:predicted={predicted_id}"
    else:
        # Predicted a disabled/unregistered model — fall back to the same
        # safety net the rule-based router uses, same reasoning: never
        # silently route to nothing.
        target = model_lookup.get(DEFAULT_MODEL_ID)
        if target is None or not target.enabled:
            raise RoutingError(
                f"learned-v1 predicted {predicted_id!r} (unavailable) and the default "
                f"model {DEFAULT_MODEL_ID!r} is also unavailable"
            )
        rationale = (
            f"learned-v1 predicted {predicted_id}, but that model is unavailable/disabled "
            f"right now — falling back to {DEFAULT_MODEL_ID}. {DEFAULT_RATIONALE}"
        )
        matched_rule = f"learned-v1:fallback-from={predicted_id}"

    return RoutingDecision(
        category=analysis.category,
        category_source=analysis.category_source,
        difficulty=analysis.difficulty,
        structured_output_required=analysis.structured_output_required,
        confidence=confidence,
        selected_model_id=target.id,
        selected_provider=target.provider,
        router_version=LEARNED_ROUTER_VERSION,
        rationale=rationale,
        matched_rule=matched_rule,
    )
