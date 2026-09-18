"""Rule-based router: turns a RequestAnalysis into a RoutingDecision by
evaluating DEFAULT_RULES in order and taking the first match whose target
model is currently enabled.
"""

from dataclasses import dataclass

from app.models.enums import TaskCategory, TaskDifficulty
from app.providers.registry import ModelConfig
from app.routing.analyzer import RequestAnalysis
from app.routing.rules import DEFAULT_MODEL_ID, DEFAULT_RATIONALE, DEFAULT_RULES, ROUTER_VERSION


class RoutingError(Exception):
    """Raised when no rule matches and the default model isn't available either."""


@dataclass(frozen=True)
class RoutingDecision:
    category: TaskCategory
    category_source: str
    difficulty: TaskDifficulty
    structured_output_required: bool
    selected_model_id: str
    selected_provider: str
    router_version: str
    rationale: str
    matched_rule: str | None


def _decision_for(analysis: RequestAnalysis, model: ModelConfig, rationale: str, rule_name: str | None) -> RoutingDecision:
    return RoutingDecision(
        category=analysis.category,
        category_source=analysis.category_source,
        difficulty=analysis.difficulty,
        structured_output_required=analysis.structured_output_required,
        selected_model_id=model.id,
        selected_provider=model.provider,
        router_version=ROUTER_VERSION,
        rationale=rationale,
        matched_rule=rule_name,
    )


def decide_route(analysis: RequestAnalysis, model_lookup: dict[str, ModelConfig]) -> RoutingDecision:
    """model_lookup maps model config id -> ModelConfig (see providers/registry.py).

    Rules are tried in order; a rule only "counts" as matching if its
    target model is present and enabled, so a disabled model doesn't
    silently break routing — the next rule (or the default) takes over.
    """
    for rule in DEFAULT_RULES:
        if not rule.matches(analysis):
            continue
        model = model_lookup.get(rule.model_id)
        if model is None or not model.enabled:
            continue
        return _decision_for(analysis, model, rule.rationale, rule.name)

    default_model = model_lookup.get(DEFAULT_MODEL_ID)
    if default_model is None or not default_model.enabled:
        raise RoutingError(
            f"no routing rule matched and the default model {DEFAULT_MODEL_ID!r} "
            "is not available/enabled"
        )
    return _decision_for(analysis, default_model, DEFAULT_RATIONALE, None)
