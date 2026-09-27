import json
import tempfile
from pathlib import Path

import joblib
import pytest

from app.routing.learned import train_escalation
from app.routing.learned.escalation_dataset import MODEL_120B_ID, MODEL_20B_ID


def _write_task(dir_, task_id, category, prompt):
    # `category` here is only the authored/ground-truth label in the task
    # file - build_escalation_rows extracts FEATURES via analyze_request
    # (the same heuristic used at serve time, deliberately not this
    # field), which guesses category from keywords in `prompt` itself.
    # The prompt has to actually contain a trigger keyword for the
    # synthetic pattern to be learnable through the real pipeline.
    (dir_ / f"{task_id}.json").write_text(
        json.dumps(
            {
                "id": task_id,
                "title": task_id,
                "category": category,
                "difficulty": "medium",
                "prompt": prompt,
                "evaluation_type": "valid_json",
                "expected_output": "x",
                "metadata": {},
            }
        )
    )


def _execution(task_id, model_id, evaluation_status, latency, cost):
    return {
        "task_id": task_id,
        "model_config_id": model_id,
        "status": "success",
        "evaluation_status": evaluation_status,
        "latency_ms": latency,
        "estimated_cost_usd": cost,
    }


def _synthetic_dataset(tmp_path, n_tasks=24):
    """An unambiguous, genuinely learnable pattern: prompts containing
    "summarize" (so analyze_request's real keyword heuristic actually
    detects category=summarization, not just the authored field) need
    120b (20b wrong, 120b right); every other prompt is fine on 20b
    (both right) - a sanity check on the PIPELINE, not a claim about the
    real, much noisier dataset (that result lives in experiments/
    results/ and docs/case-study/DECISIONS.md, 2026-09-27).
    """
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    rows = []
    for i in range(n_tasks):
        task_id = f"task-{i:03d}"
        if i % 4 == 0:
            category, prompt = "summarization", f"Summarize this article, item {i}."
        else:
            category, prompt = "reasoning", f"Explain your thinking on this open-ended question, item {i}."
        _write_task(tasks_dir, task_id, category, prompt)
        if category == "summarization":
            rows.append(_execution(task_id, MODEL_20B_ID, "incorrect", 500.0, 0.0001))
            rows.append(_execution(task_id, MODEL_120B_ID, "correct", 900.0, 0.0005))
        else:
            rows.append(_execution(task_id, MODEL_20B_ID, "correct", 500.0, 0.0001))
            rows.append(_execution(task_id, MODEL_120B_ID, "correct", 900.0, 0.0005))
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps({"executions": rows}))
    return tasks_dir, results_path


def test_run_refuses_a_too_small_dataset(tmp_path):
    tasks_dir, results_path = _synthetic_dataset(tmp_path, n_tasks=4)
    with pytest.raises(RuntimeError, match="refusing to train"):
        train_escalation.run(
            results_path=results_path,
            benchmarks_dir=tasks_dir,
            artifact_path=tmp_path / "artifact.joblib",
            manifest_path=tmp_path / "manifest.json",
        )


def test_run_produces_a_complete_manifest_and_a_loadable_artifact(tmp_path):
    tasks_dir, results_path = _synthetic_dataset(tmp_path, n_tasks=24)
    artifact_path = tmp_path / "artifact.joblib"
    manifest_path = tmp_path / "manifest.json"

    manifest = train_escalation.run(
        results_path=results_path,
        benchmarks_dir=tasks_dir,
        artifact_path=artifact_path,
        manifest_path=manifest_path,
    )

    assert manifest["router_version"] == "learned-v2"
    assert manifest["n_training_rows"] == 24
    assert manifest["chosen_algorithm"] in ("logistic_regression", "decision_tree")
    assert set(manifest["candidate_algorithms"]) == {"logistic_regression", "decision_tree"}
    assert set(manifest["baselines_same_92_rows"]) == {"always-20b", "always-120b", "d2-baseline", "oracle"}
    for result in manifest["candidate_algorithms"].values():
        assert 0.0 <= result["accuracy"] <= 1.0
    for result in manifest["baselines_same_92_rows"].values():
        assert 0.0 <= result["accuracy"] <= 1.0
    assert isinstance(manifest["learned_beats_d2"], bool)
    assert isinstance(manifest["learned_beats_always_120b"], bool)

    assert artifact_path.exists()
    assert manifest_path.exists()
    loaded = joblib.load(artifact_path)
    assert hasattr(loaded, "predict")
    assert hasattr(loaded, "predict_proba")


def test_learned_router_recovers_the_unambiguous_synthetic_pattern(tmp_path):
    """Distinguishes 'the pipeline is broken' from 'the real data doesn't
    support a good model' (the real dataset's honest 88.0% vs D2's 90.2%
    is a data/signal problem, verified here to not also be a bug)."""
    tasks_dir, results_path = _synthetic_dataset(tmp_path, n_tasks=24)
    manifest = train_escalation.run(
        results_path=results_path,
        benchmarks_dir=tasks_dir,
        artifact_path=tmp_path / "artifact.joblib",
        manifest_path=tmp_path / "manifest.json",
    )
    chosen = manifest["learned_router_system_metrics_loocv"]
    assert chosen["accuracy"] >= 0.9


def test_oracle_is_always_at_least_as_good_as_every_other_baseline(tmp_path):
    tasks_dir, results_path = _synthetic_dataset(tmp_path, n_tasks=24)
    manifest = train_escalation.run(
        results_path=results_path,
        benchmarks_dir=tasks_dir,
        artifact_path=tmp_path / "artifact.joblib",
        manifest_path=tmp_path / "manifest.json",
    )
    baselines = manifest["baselines_same_92_rows"]
    oracle_accuracy = baselines["oracle"]["accuracy"]
    assert oracle_accuracy >= baselines["always-20b"]["accuracy"]
    assert oracle_accuracy >= baselines["always-120b"]["accuracy"]
    assert oracle_accuracy >= baselines["d2-baseline"]["accuracy"]
    assert oracle_accuracy >= manifest["learned_router_system_metrics_loocv"]["accuracy"]


def test_manifest_is_reproducible_with_the_same_fixed_seed(tmp_path):
    tasks_dir, results_path = _synthetic_dataset(tmp_path, n_tasks=24)
    manifest_1 = train_escalation.run(
        results_path=results_path,
        benchmarks_dir=tasks_dir,
        artifact_path=tmp_path / "a1.joblib",
        manifest_path=tmp_path / "m1.json",
    )
    manifest_2 = train_escalation.run(
        results_path=results_path,
        benchmarks_dir=tasks_dir,
        artifact_path=tmp_path / "a2.joblib",
        manifest_path=tmp_path / "m2.json",
    )
    assert manifest_1["chosen_algorithm"] == manifest_2["chosen_algorithm"]
    assert (
        manifest_1["learned_router_system_metrics_loocv"]
        == manifest_2["learned_router_system_metrics_loocv"]
    )


def test_real_project_data_trains_successfully():
    """Regression check against the actual committed 92-row real dataset -
    just confirms the full pipeline runs end to end on real data without
    asserting specific numbers here (those are documented, with full
    context, in docs/case-study/DECISIONS.md and the committed
    artifacts/learned-v2.manifest.json - duplicating exact floats in a
    unit test would make routine retraining noise look like a test
    failure)."""
    with tempfile.TemporaryDirectory() as tmp:
        manifest = train_escalation.run(
            artifact_path=Path(tmp) / "artifact.joblib",
            manifest_path=Path(tmp) / "manifest.json",
        )
    assert manifest["n_training_rows"] == 92
    assert manifest["excluded_task_counts"] == {"no_ground_truth_for_both_models": 12}
