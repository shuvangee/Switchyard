"""Fixed-model router strategies: "always-20b" and "always-120b" — the
two single-model baselines every comparison in this project is measured
against (see /compare and docs/case-study/EXPERIMENTS.md). Exposed as
selectable Playground strategies (V4) purely so a visitor can directly
compare "what if every request just went to the cheap/expensive model"
against D2 and learned-v2, without needing to read the case study to
understand the baseline. Not a new research strategy — the numbers
behind them were already measured in V3; this just makes the two
constant rules selectable, the same way D2 and learned-v2 already are.
"""

from dataclasses import dataclass

from app.providers.registry import ModelConfig
from app.routing.analyzer import RequestAnalysis
from app.routing.learned.escalation_dataset import MODEL_120B_ID, MODEL_20B_ID
from app.routing.router import RoutingDecision, RoutingError, estimate_confidence
from app.routing.rules import DEFAULT_MODEL_ID, DEFAULT_RATIONALE

ALWAYS_20B_ROUTER_VERSION = "always-20b"
ALWAYS_120B_ROUTER_VERSION = "always-120b"


@dataclass(frozen=True)
class _FixedStrategy:
    router_version: str
    primary_model_id: str
    rationale: str


_STRATEGIES = {
    ALWAYS_20B_ROUTER_VERSION: _FixedStrategy(
        ALWAYS_20B_ROUTER_VERSION,
        MODEL_20B_ID,
        "always-20b: every request goes to groq-gpt-oss-20b, regardless of category or "
        "difficulty — the cheapest single-model baseline, measured at 88.0% accuracy on the "
        "92-task benchmark (see /compare).",
    ),
    ALWAYS_120B_ROUTER_VERSION: _FixedStrategy(
        ALWAYS_120B_ROUTER_VERSION,
        MODEL_120B_ID,
        "always-120b: every request goes to groq-gpt-oss-120b, regardless of category or "
        "difficulty — the strongest single-model baseline, measured at 90.2% accuracy but "
        "1.86x the nominal cost and 1.44x the latency of always-20b (see /compare).",
    ),
}


def decide_route_fixed(
    router_version: str, analysis: RequestAnalysis, model_lookup: dict[str, ModelConfig]
) -> RoutingDecision:
    strategy = _STRATEGIES[router_version]
    model = model_lookup.get(strategy.primary_model_id)
    rationale = strategy.rationale
    matched_rule = router_version

    if model is None or not model.enabled:
        fallback = model_lookup.get(DEFAULT_MODEL_ID)
        if fallback is None or not fallback.enabled:
            raise RoutingError(
                f"{router_version} targets {strategy.primary_model_id!r} (unavailable), and the "
                f"default model {DEFAULT_MODEL_ID!r} is also unavailable"
            )
        rationale = f"{rationale} {strategy.primary_model_id} is unavailable/disabled — falling back to {DEFAULT_MODEL_ID}. {DEFAULT_RATIONALE}"
        matched_rule = f"{router_version}+fallback={DEFAULT_MODEL_ID}"
        model = fallback

    return RoutingDecision(
        category=analysis.category,
        category_source=analysis.category_source,
        difficulty=analysis.difficulty,
        structured_output_required=analysis.structured_output_required,
        confidence=estimate_confidence(analysis),
        selected_model_id=model.id,
        selected_provider=model.provider,
        router_version=router_version,
        rationale=rationale,
        matched_rule=matched_rule,
        router_score=None,
    )
