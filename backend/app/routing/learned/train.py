"""V3 training pipeline.

raw data (experiments/results/*.json)
  -> dataset construction (dataset.build_training_rows)
  -> feature processing (features.encode)
  -> evaluation via leave-one-out cross-validation (NOT a train/val/test
     split — see below)
  -> comparison against baselines (always-cheapest, always-strongest,
     V1 rule-based, random)
  -> saved router artifact (learned/artifacts/learned-v1.joblib + .json
     manifest)

WHY LEAVE-ONE-OUT, NOT A TRAIN/VAL/TEST SPLIT: with 24 total rows, a
conventional 80/20 split leaves a ~5-row test set — a single such split's
accuracy is dominated by noise (getting 1 extra row right or wrong is a
20-point swing). Leave-one-out (train on 23, predict the 1 held out,
repeat 24 times) uses every row as a held-out test exactly once, which is
the standard, defensible choice for a dataset this small — not a
workaround, the textbook-correct method here. It still prevents leakage
the same way a split would: each held-out row's prediction never saw that
row's own label during its training.

The final saved artifact is trained on ALL 24 rows (not held out) — LOOCV
estimates how a model trained on data-of-this-size generalizes; the
deployed model should still use every real observation available.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text

from app.routing.analyzer import analyze_request
from app.routing.learned.dataset import Candidate, TrainingRow, build_training_rows
from app.routing.learned.features import encode
from app.routing.rules import ROUTER_VERSION as V1_ROUTER_VERSION
from app.routing.router import RoutingError, decide_route
from app.providers.registry import get_model_registry

LEARNED_ROUTER_VERSION = "learned-v1"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_PATH = ARTIFACT_DIR / "learned-v1.joblib"
MANIFEST_PATH = ARTIFACT_DIR / "learned-v1.manifest.json"

_ALWAYS_CHEAPEST_MODEL_ID = "mock-fast-v1"  # lowest input+output cost/1k in the registry
_ALWAYS_STRONGEST_MODEL_ID = "mock-accurate-v1"  # the mock registry's designated "capable" tier


def _candidate_lookup(row: TrainingRow) -> dict[str, Candidate]:
    return {c.model_config_id: c for c in row.candidates}


def _outcome_for(row: TrainingRow, model_id: str) -> Candidate | None:
    """The recorded (correct, cost) outcome for `model_id` on this task, if
    we have one. None means: we have no ground truth for this hypothetical
    routing decision — never guessed, always reported as its own bucket.
    """
    return _candidate_lookup(row).get(model_id)


def _new_tree() -> DecisionTreeClassifier:
    # Shallow on purpose: N=24, 3 imbalanced classes (14/8/2). A deeper
    # tree would fit noise, not signal, and stop being interpretable.
    return DecisionTreeClassifier(max_depth=2, min_samples_leaf=2, random_state=0)


def _leave_one_out_predictions(rows: list[TrainingRow]) -> list[str]:
    """Returns one predicted target model_id per row, each predicted by a
    model trained on the other 23 rows only.
    """
    analyses = [r.analysis for r in rows]
    encoded = encode(analyses)
    y = [r.target_model_id for r in rows]

    predictions = []
    n = len(rows)
    for held_out_idx in range(n):
        train_idx = [i for i in range(n) if i != held_out_idx]
        clf = _new_tree()
        clf.fit(encoded.matrix[train_idx], [y[i] for i in train_idx])
        pred = clf.predict(encoded.matrix[held_out_idx : held_out_idx + 1])[0]
        predictions.append(pred)
    return predictions


def _v1_rule_based_predictions(rows: list[TrainingRow]) -> list[str | None]:
    model_lookup = {m.id: m for m in get_model_registry()}
    predictions = []
    for row in rows:
        try:
            decision = decide_route(row.analysis, model_lookup)
            predictions.append(decision.selected_model_id)
        except RoutingError:
            predictions.append(None)
    return predictions


def _random_expected_outcome(row: TrainingRow) -> tuple[float, float]:
    """Expected-value random baseline: uniform over this row's ACTUAL
    candidates (not a single noisy sampled draw, which would depend on
    an arbitrary seed) -> (p_correct, expected_cost_usd).
    """
    candidates = [c for c in row.candidates if c.estimated_cost_usd is not None]
    if not candidates:
        return 0.0, 0.0
    p_correct = sum(1 for c in candidates if c.correct) / len(candidates)
    expected_cost = sum(c.estimated_cost_usd for c in candidates) / len(candidates)
    return p_correct, expected_cost


def _summarize(name: str, rows: list[TrainingRow], predictions: list[str | None]) -> dict:
    correct = 0
    unknown = 0
    total_cost = 0.0
    priced_n = 0
    for row, pred in zip(rows, predictions):
        if pred is None:
            unknown += 1
            continue
        outcome = _outcome_for(row, pred)
        if outcome is None or outcome.estimated_cost_usd is None:
            unknown += 1
            continue
        priced_n += 1
        if outcome.correct:
            correct += 1
        total_cost += outcome.estimated_cost_usd
    evaluable = len(rows) - unknown
    return {
        "strategy": name,
        "n_rows": len(rows),
        "n_evaluable": evaluable,
        "n_unknown_outcome": unknown,
        "accuracy_on_evaluable": (correct / evaluable) if evaluable else None,
        "total_cost_usd_on_evaluable": total_cost,
        "avg_cost_usd_on_evaluable": (total_cost / priced_n) if priced_n else None,
    }


def _summarize_random(rows: list[TrainingRow]) -> dict:
    p_corrects, costs = zip(*(_random_expected_outcome(r) for r in rows))
    return {
        "strategy": "random",
        "n_rows": len(rows),
        "n_evaluable": len(rows),
        "n_unknown_outcome": 0,
        "accuracy_on_evaluable": sum(p_corrects) / len(rows),
        "total_cost_usd_on_evaluable": sum(costs),
        "avg_cost_usd_on_evaluable": sum(costs) / len(rows),
    }


def run(
    result_files: list[Path] | None = None,
    benchmarks_dir: Path | None = None,
    artifact_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict:
    artifact_path = artifact_path or ARTIFACT_PATH
    manifest_path = manifest_path or MANIFEST_PATH

    rows, excluded = build_training_rows(result_files=result_files, benchmarks_dir=benchmarks_dir)
    if len(rows) < 5:
        raise RuntimeError(
            f"only {len(rows)} training rows available (excluded: {excluded}) — "
            "refusing to train on a dataset this small without an explicit override."
        )

    loo_predictions = _leave_one_out_predictions(rows)
    always_cheapest = [_ALWAYS_CHEAPEST_MODEL_ID] * len(rows)
    always_strongest = [_ALWAYS_STRONGEST_MODEL_ID] * len(rows)
    v1_predictions = _v1_rule_based_predictions(rows)

    comparison = [
        _summarize(LEARNED_ROUTER_VERSION, rows, loo_predictions),
        _summarize("always-cheapest", rows, always_cheapest),
        _summarize("always-strongest", rows, always_strongest),
        _summarize(V1_ROUTER_VERSION, rows, v1_predictions),
        _summarize_random(rows),
    ]

    # Final deployed artifact: trained on ALL rows, not held out.
    encoded = encode([r.analysis for r in rows])
    final_model = _new_tree()
    final_model.fit(encoded.matrix, [r.target_model_id for r in rows])
    tree_text = export_text(final_model, feature_names=encoded.names)

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    import joblib

    joblib.dump(final_model, artifact_path)

    manifest = {
        "router_version": LEARNED_ROUTER_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_training_rows": len(rows),
        "excluded_task_counts": excluded,
        "feature_names": encoded.names,
        "target_classes": sorted(set(r.target_model_id for r in rows)),
        "training_target_definition": (
            "cheapest candidate model with a recorded CORRECT outcome for "
            "each task, among tasks with a deterministic evaluator"
        ),
        "evaluation_method": (
            f"leave-one-out cross-validation (n={len(rows)} too small for a held-out split)"
        ),
        "comparison": comparison,
        "decision_tree_text": tree_text,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    return manifest


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
