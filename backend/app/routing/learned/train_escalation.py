"""V3 escalation router training pipeline — the actual deliverable of the
"V3: learned routing" project stage. Builds a binary classifier that
predicts whether a request should escalate from groq-gpt-oss-20b to
groq-gpt-oss-120b, using only pre-execution features, trained and
evaluated on the 92 real Groq-graded benchmark tasks.

Distinct from routing/learned/train.py (the earlier, exploratory
"cheapest correct candidate" multiclass model across a mixed mock/
gemini/groq dataset — that one is documented as NOT recommended for
real use and is left untouched, still backing the "learned-v1" router
version for comparison/history). This pipeline is versioned
"learned-v2" — a materially different target, dataset, and evaluation
methodology, not a retrain of the same thing. See
docs/case-study/DECISIONS.md (2026-09-27).

EVALUATION METHODOLOGY: leave-one-out cross-validation (LOOCV), same
method already established for this project's small-N routing analyses
(routing/learned/train.py, 2026-09-22 decision; scripts/analyze_simple_
routing_baselines.py, 2026-09-24 decision) — at 92 rows with only 5
positive (escalate) examples, a held-out test split would leave far too
few positive examples in the test fold to mean anything.

Critically, LOOCV here is SYSTEM-level, not classifier-level: for each
held-out task, the classifier trained on the other 91 rows predicts
escalate/don't-escalate, that prediction selects a model (120b or 20b),
and the REAL recorded outcome/cost/latency for THAT model on that exact
task (never an average, never the other model's numbers) is what gets
aggregated into accuracy/cost/latency. A classifier can be "accurate" at
predicting the label while still being a worse ROUTER than a simpler
rule if its errors land on expensive tasks — system-level LOOCV is what
actually answers the question this project cares about.

Two candidate algorithms are compared (no neural networks, no GPU, no
LLM fine-tuning, per the project's explicit scope): logistic regression
and a shallow decision tree, both with class_weight="balanced" (5/92
positive examples is heavily imbalanced) and a fixed random_state for
reproducibility. The final router is whichever wins on LOOCV SYSTEM
accuracy — not raw classifier accuracy — with ties broken toward the
simpler/more directly auditable model (a decision path a person can
read, over regression coefficients that need feature-scale context).

Run from the repo root:

    cd backend && source .venv/bin/activate
    python -m app.routing.learned.train_escalation

or, equivalently, the wrapper at scripts/train_router.py.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, export_text

from app.models.enums import TaskCategory
from app.routing.learned.escalation_dataset import (
    MODEL_120B_ID,
    MODEL_20B_ID,
    EscalationRow,
    build_escalation_rows,
)
from app.routing.learned.features import FEATURE_NAMES, encode

ESCALATION_ROUTER_VERSION = "learned-v2"
RANDOM_SEED = 0
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_PATH = ARTIFACT_DIR / "learned-v2.joblib"
MANIFEST_PATH = ARTIFACT_DIR / "learned-v2.manifest.json"

MIN_ROWS = 20  # refuse to train on a dataset too small to say anything


def _new_logistic_regression() -> LogisticRegression:
    return LogisticRegression(class_weight="balanced", random_state=RANDOM_SEED, max_iter=1000)


def _new_tree() -> DecisionTreeClassifier:
    # Shallow and leaf-constrained on purpose (same reasoning as
    # routing/learned/train.py's tree): 92 rows, 5 positives, cannot
    # support a deep tree without memorizing noise.
    return DecisionTreeClassifier(
        max_depth=2, min_samples_leaf=2, class_weight="balanced", random_state=RANDOM_SEED
    )


def _select_model(escalate: bool) -> str:
    return MODEL_120B_ID if escalate else MODEL_20B_ID


def _system_metrics(rows: list[EscalationRow], choices: list[bool]) -> dict[str, Any]:
    """choices[i] = whether row i's request was routed to 120b. Scored
    using each task's REAL recorded correctness/cost/latency for
    whichever model was actually chosen for it — no averages substituted
    where real per-task values exist.
    """
    n = len(rows)
    correct = 0
    cost = 0.0
    latency_sum = 0.0
    n_120b = 0
    for row, escalate in zip(rows, choices, strict=True):
        if escalate:
            n_120b += 1
            correct += row.correct_120b
            cost += row.cost_120b_usd
            latency_sum += row.latency_120b_ms
        else:
            correct += row.correct_20b
            cost += row.cost_20b_usd
            latency_sum += row.latency_20b_ms
    return {
        "accuracy": correct / n,
        "correct": correct,
        "n": n,
        "pct_120b": n_120b / n,
        "nominal_cost_usd": cost,
        "avg_latency_ms": latency_sum / n,
    }


def _loocv_system_metrics(rows: list[EscalationRow], make_model) -> dict[str, Any]:
    """True leave-one-out cross-validation: for each row, fit a fresh
    model on every OTHER row, predict the held-out row's label, and use
    that prediction (never the row's own true label) to pick a model.
    No held-out row's own outcome ever informs the model used to predict
    it — this is what makes the resulting accuracy an honest, out-of-
    sample estimate rather than an in-sample number.
    """
    choices: list[bool] = []
    for i in range(len(rows)):
        train_rows = rows[:i] + rows[i + 1 :]
        x_train = encode([r.analysis for r in train_rows]).matrix
        y_train = np.array([r.escalate for r in train_rows], dtype=int)
        model = make_model()
        model.fit(x_train, y_train)
        x_held_out = encode([rows[i].analysis]).matrix
        predicted = bool(model.predict(x_held_out)[0])
        choices.append(predicted)
    return _loocv_choices_to_metrics(rows, choices)


def _loocv_choices_to_metrics(rows: list[EscalationRow], choices: list[bool]) -> dict[str, Any]:
    metrics = _system_metrics(rows, choices)
    metrics["escalate_predictions"] = sum(choices)
    return metrics


def _baseline_always_20b(rows: list[EscalationRow]) -> dict[str, Any]:
    return _system_metrics(rows, [False] * len(rows))


def _baseline_always_120b(rows: list[EscalationRow]) -> dict[str, Any]:
    return _system_metrics(rows, [True] * len(rows))


def _baseline_d2(rows: list[EscalationRow]) -> dict[str, Any]:
    # "summarization -> 120b, everything else -> 20b" — the LOOCV-
    # validated simple baseline from docs/case-study/DECISIONS.md
    # (2026-09-24). Recomputed directly here (not imported from the
    # scripts/ analysis tooling) so this manifest is self-contained and
    # reproducible from this module alone.
    choices = [row.analysis.category == TaskCategory.SUMMARIZATION for row in rows]
    return _system_metrics(rows, choices)


def _baseline_oracle(rows: list[EscalationRow]) -> dict[str, Any]:
    # Escalate only when doing so is actually correct-and-necessary
    # (120b right, 20b wrong) — the theoretical upper bound, not an
    # implementable strategy (it requires already knowing the answer).
    choices = [row.correct_120b and not row.correct_20b for row in rows]
    return _system_metrics(rows, choices)


def run(
    results_path: Path | None = None,
    benchmarks_dir: Path | None = None,
    artifact_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    artifact_path = artifact_path or ARTIFACT_PATH
    manifest_path = manifest_path or MANIFEST_PATH

    rows, excluded = build_escalation_rows(results_path=results_path, benchmarks_dir=benchmarks_dir)
    if len(rows) < MIN_ROWS:
        raise RuntimeError(
            f"refusing to train on {len(rows)} rows (minimum {MIN_ROWS}) — "
            "too small for leave-one-out cross-validation to mean anything"
        )

    candidates = {
        "logistic_regression": _new_logistic_regression,
        "decision_tree": _new_tree,
    }
    candidate_results = {name: _loocv_system_metrics(rows, make) for name, make in candidates.items()}

    baselines = {
        "always-20b": _baseline_always_20b(rows),
        "always-120b": _baseline_always_120b(rows),
        "d2-baseline": _baseline_d2(rows),
        "oracle": _baseline_oracle(rows),
    }

    # Pick the winner primarily by LOOCV system accuracy — but at 92 rows
    # (5 positive examples), a 1-task accuracy difference is noise, not
    # signal: two candidates within one task's worth of each other
    # (1/len(rows)) are treated as practically tied and broken by cost,
    # then by interpretability (a printed decision path over regression
    # coefficients that need feature-scale context to read). This is not
    # a tie-break of last resort here — it is expected to matter, since
    # nothing about a handful of positive examples supports resolving a
    # single-task accuracy gap as a real signal.
    noise_margin = 1.0 / len(rows)
    best_accuracy = max(result["accuracy"] for result in candidate_results.values())
    practically_tied = [
        name
        for name, result in candidate_results.items()
        if best_accuracy - result["accuracy"] <= noise_margin + 1e-9
    ]
    if len(practically_tied) == 1:
        best_name = practically_tied[0]
        tie_break_reason = None
    else:
        # Break by lower nominal cost first (the project's actual
        # objective), then prefer decision_tree for interpretability.
        best_name = min(
            practically_tied,
            key=lambda name: (candidate_results[name]["nominal_cost_usd"], name != "decision_tree"),
        )
        tie_break_reason = (
            f"{practically_tied} were within {noise_margin:.3f} accuracy (one task's worth on "
            f"{len(rows)} rows) — not distinguishable from noise at this sample size. Broken by "
            f"lower LOOCV nominal cost (the project's actual objective), then by interpretability."
        )
    chosen_make = candidates[best_name]

    # Final artifact: refit the CHOSEN algorithm on all 92 rows. This is
    # a different object from any of the 92 leave-one-out models above —
    # standard practice, same as routing/learned/train.py's precedent —
    # worth being explicit that the deployed model and the LOOCV numbers
    # describing it are not literally the same fitted object.
    x_all = encode([r.analysis for r in rows]).matrix
    y_all = np.array([r.escalate for r in rows], dtype=int)
    final_model = chosen_make()
    final_model.fit(x_all, y_all)

    interpretability: dict[str, Any] = {}
    if best_name == "decision_tree":
        interpretability["decision_tree_text"] = export_text(final_model, feature_names=FEATURE_NAMES)
    else:
        interpretability["logistic_regression_coefficients"] = dict(
            zip(FEATURE_NAMES, [round(c, 4) for c in final_model.coef_[0].tolist()], strict=True)
        )
        interpretability["logistic_regression_intercept"] = round(float(final_model.intercept_[0]), 4)

    manifest: dict[str, Any] = {
        "router_version": ESCALATION_ROUTER_VERSION,
        "trained_at": datetime.now(UTC).isoformat(),
        "random_seed": RANDOM_SEED,
        "n_training_rows": len(rows),
        "excluded_task_counts": excluded,
        "feature_names": FEATURE_NAMES,
        "training_target_definition": (
            "escalate=True iff groq-gpt-oss-120b is correct AND groq-gpt-oss-20b is "
            "incorrect on the real recorded evaluation (the only case where paying for "
            "120b changes the outcome); escalate=False for both-correct (20b already "
            "sufficient), only-20b-correct (120b would be wrong), and both-incorrect "
            "(escalating buys nothing) — see this module's docstring and "
            "docs/case-study/DECISIONS.md (2026-09-27)."
        ),
        "candidate_algorithms": {
            name: {k: v for k, v in result.items()} for name, result in candidate_results.items()
        },
        "chosen_algorithm": best_name,
        "chosen_algorithm_reason": (
            tie_break_reason
            or f"strictly highest LOOCV system accuracy ({candidate_results[best_name]['accuracy']:.3f}), "
            f"more than {noise_margin:.3f} (one task) ahead of the alternative"
        ),
        "evaluation_method": (
            "leave-one-out cross-validation, SYSTEM-level (accuracy/cost/latency use the "
            "real recorded outcome of whichever model each held-out prediction selected, "
            "not classifier accuracy on the label alone)"
        ),
        "learned_router_system_metrics_loocv": candidate_results[best_name],
        "baselines_same_92_rows": baselines,
        "learned_beats_d2": candidate_results[best_name]["accuracy"] > baselines["d2-baseline"]["accuracy"],
        "learned_beats_always_120b": (
            candidate_results[best_name]["accuracy"] > baselines["always-120b"]["accuracy"]
        ),
        **interpretability,
    }

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, artifact_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    return manifest


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
