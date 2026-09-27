"""D2 baseline router: "summarization -> groq-gpt-oss-120b, everything
else -> groq-gpt-oss-20b" — the LOOCV-validated simple routing rule from
the V2.6 simple-routing-baselines checkpoint (see
docs/case-study/DECISIONS.md, 2026-09-24, and
experiments/results/simple-routing-baselines.md). No trained artifact:
a fixed, one-line, fully auditable rule, kept selectable alongside V3's
learned router (learned-v2) for direct comparison — it currently beats
learned-v2 on every measured system metric, so it is the preferred
production strategy; see docs/case-study/DECISIONS.md (2026-09-27).
"""

from dataclasses import dataclass

from app.models.enums import TaskCategory
from app.providers.registry import ModelConfig
from app.routing.analyzer import RequestAnalysis
from app.routing.learned.escalation_dataset import MODEL_120B_ID, MODEL_20B_ID
from app.routing.router import RoutingDecision, RoutingError, estimate_confidence
from app.routing.rules import DEFAULT_MODEL_ID, DEFAULT_RATIONALE

D2_ROUTER_VERSION = "d2-baseline"

_RATIONALE_SUMMARIZATION = (
    "D2 baseline: category=summarization -> groq-gpt-oss-120b. This is the one category "
    "where the larger model showed a real, LOOCV-validated accuracy edge (see "
    "docs/case-study/DECISIONS.md, 2026-09-24)."
)
_RATIONALE_DEFAULT = (
    "D2 baseline: category is not summarization -> groq-gpt-oss-20b (default; no observed "
    "quality edge for the larger model on this category, LOOCV-validated)."
)


@dataclass(frozen=True)
class _Pick:
    model_id: str
    rationale: str
    matched_rule: str


def _pick(analysis: RequestAnalysis) -> _Pick:
    if analysis.category == TaskCategory.SUMMARIZATION:
        return _Pick(MODEL_120B_ID, _RATIONALE_SUMMARIZATION, "d2-summarization-override")
    return _Pick(MODEL_20B_ID, _RATIONALE_DEFAULT, "d2-default")


def decide_route_d2(
    analysis: RequestAnalysis, model_lookup: dict[str, ModelConfig]
) -> RoutingDecision:
    pick = _pick(analysis)
    model = model_lookup.get(pick.model_id)
    rationale = pick.rationale
    matched_rule = pick.matched_rule

    if model is None or not model.enabled:
        # Fall back to the other Groq model first — a disabled target
        # shouldn't take the whole strategy down.
        fallback_id = MODEL_20B_ID if pick.model_id == MODEL_120B_ID else MODEL_120B_ID
        fallback_model = model_lookup.get(fallback_id)
        if fallback_model is not None and fallback_model.enabled:
            rationale = f"{pick.rationale} {pick.model_id} is unavailable/disabled — falling back to {fallback_id}."
            matched_rule = f"{pick.matched_rule}+fallback={fallback_id}"
            model = fallback_model
        else:
            # Neither Groq model is available (e.g. no GROQ_API_KEY
            # configured) — fall back to the global default rather than
            # fail outright, same safety net every other strategy uses.
            default_model = model_lookup.get(DEFAULT_MODEL_ID)
            if default_model is None or not default_model.enabled:
                raise RoutingError(
                    f"D2 baseline picked {pick.model_id!r} (unavailable), its Groq counterpart "
                    f"is also unavailable, and the default model {DEFAULT_MODEL_ID!r} is too"
                )
            rationale = f"{pick.rationale} Neither Groq model is available — falling back to {DEFAULT_MODEL_ID}. {DEFAULT_RATIONALE}"
            matched_rule = f"{pick.matched_rule}+fallback={DEFAULT_MODEL_ID}"
            model = default_model

    return RoutingDecision(
        category=analysis.category,
        category_source=analysis.category_source,
        difficulty=analysis.difficulty,
        structured_output_required=analysis.structured_output_required,
        confidence=estimate_confidence(analysis),
        selected_model_id=model.id,
        selected_provider=model.provider,
        router_version=D2_ROUTER_VERSION,
        rationale=rationale,
        matched_rule=matched_rule,
        router_score=None,  # deterministic rule — no model score to report
    )
