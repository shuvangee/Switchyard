"""Rule-based router: turns a RequestAnalysis into a RoutingDecision by
evaluating DEFAULT_RULES in order and taking the first match whose target
model is currently enabled.

Also computes routing confidence (see estimate_confidence) and, when it's
LOW, escalates the *initial* model choice directly rather than trusting
the normal rule — this is the "routing confidence too low -> stronger
model" trigger from the V2 design; the other two triggers (validation
failure, provider unavailable) are reactive and live in
routing/service.py's retry loop instead, since they only make sense after
a response exists.
"""

from dataclasses import dataclass

from app.models.enums import ConfidenceLevel, TaskCategory, TaskDifficulty
from app.providers.registry import ModelConfig
from app.routing.analyzer import RequestAnalysis
from app.routing.rules import (
    DEFAULT_MODEL_ID,
    DEFAULT_RATIONALE,
    DEFAULT_RULES,
    ESCALATION_TARGETS,
    ROUTER_VERSION,
)


class RoutingError(Exception):
    """Raised when no rule matches and the default model isn't available either."""


@dataclass(frozen=True)
class RoutingDecision:
    category: TaskCategory
    category_source: str
    difficulty: TaskDifficulty
    structured_output_required: bool
    confidence: ConfidenceLevel
    selected_model_id: str
    selected_provider: str
    router_version: str
    rationale: str
    matched_rule: str | None


def estimate_confidence(analysis: RequestAnalysis) -> ConfidenceLevel:
    """A heuristic label on how much the routing decision should be
    trusted, NOT a statistically calibrated probability — nothing here has
    ever been validated against real outcomes. It reflects how the
    category was determined, not whether the eventual response will be
    correct (that's what validation checks, after the fact).

    HIGH: caller told us the category explicitly.
    LOW: the analyzer found no category signal at all and fell back to
    "reasoning" as a last resort — the weakest possible guess.
    MEDIUM: everything else (a heuristic guess that at least matched a
    specific keyword/pattern).
    """
    if analysis.category_source == "explicit":
        return ConfidenceLevel.HIGH
    if analysis.category == TaskCategory.REASONING:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.MEDIUM


def _decision_for(
    analysis: RequestAnalysis,
    model: ModelConfig,
    rationale: str,
    rule_name: str | None,
    confidence: ConfidenceLevel,
) -> RoutingDecision:
    return RoutingDecision(
        category=analysis.category,
        category_source=analysis.category_source,
        difficulty=analysis.difficulty,
        structured_output_required=analysis.structured_output_required,
        confidence=confidence,
        selected_model_id=model.id,
        selected_provider=model.provider,
        router_version=ROUTER_VERSION,
        rationale=rationale,
        matched_rule=rule_name,
    )


def _apply_low_confidence_override(
    model_id: str, rationale: str, rule_name: str | None, model_lookup: dict[str, ModelConfig]
) -> tuple[str, str, str | None]:
    """If confidence is low, prefer this model's escalation target over the
    rule's normal pick — but only if that target actually exists and is
    enabled; otherwise stick with the original pick rather than raise.
    """
    escalated_id = ESCALATION_TARGETS.get(model_id)
    if escalated_id is None:
        return model_id, rationale, rule_name
    escalated_model = model_lookup.get(escalated_id)
    if escalated_model is None or not escalated_model.enabled:
        return model_id, rationale, rule_name
    new_rationale = (
        f"{rationale} Routing confidence is low (no category signal was found in the "
        f"prompt, so this fell back to 'reasoning' by default) — escalating directly to "
        f"{escalated_id} rather than risking {model_id} on an uncertain classification."
    )
    new_rule_name = f"{rule_name}+low-confidence-escalation" if rule_name else "low-confidence-escalation"
    return escalated_id, new_rationale, new_rule_name


def decide_route(
    analysis: RequestAnalysis, model_lookup: dict[str, ModelConfig]
) -> RoutingDecision:
    """model_lookup maps model config id -> ModelConfig (see providers/registry.py).

    Rules are tried in order; a rule only "counts" as matching if its
    target model is present and enabled, so a disabled model doesn't
    silently break routing — the next rule (or the default) takes over.
    """
    confidence = estimate_confidence(analysis)

    for rule in DEFAULT_RULES:
        if not rule.matches(analysis):
            continue
        model = model_lookup.get(rule.model_id)
        if model is None or not model.enabled:
            continue
        model_id, rationale, rule_name = rule.model_id, rule.rationale, rule.name
        if confidence == ConfidenceLevel.LOW:
            model_id, rationale, rule_name = _apply_low_confidence_override(
                model_id, rationale, rule_name, model_lookup
            )
        return _decision_for(analysis, model_lookup[model_id], rationale, rule_name, confidence)

    default_model = model_lookup.get(DEFAULT_MODEL_ID)
    if default_model is None or not default_model.enabled:
        raise RoutingError(
            f"no routing rule matched and the default model {DEFAULT_MODEL_ID!r} "
            "is not available/enabled"
        )
    return _decision_for(analysis, default_model, DEFAULT_RATIONALE, None, confidence)
