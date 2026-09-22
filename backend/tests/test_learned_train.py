import json

import joblib
import pytest

from app.routing.learned import train as train_module


def _write_task(dir_, task_id, category, difficulty="easy", expected_output="7"):
    # The analyzer's heuristic difficulty is word count, not this field —
    # features must be built from the SAME signal the router sees at
    # inference time, so the prompt itself has to vary in length to match
    # the intended difficulty (a short prompt is always "easy" regardless
    # of what's authored here).
    if difficulty == "hard":
        prompt = f"What is {task_id}? " + "Please think about this carefully. " * 10
    else:
        prompt = f"What is {task_id}?"
    (dir_ / f"{task_id}.json").write_text(
        json.dumps(
            {
                "id": task_id,
                "title": task_id,
                "category": category,
                "difficulty": difficulty,
                "prompt": prompt,
                "evaluation_type": "exact_match",
                "expected_output": expected_output,
                "metadata": {},
            }
        )
    )


def _write_results(path, rows):
    path.write_text(json.dumps({"executions": rows}))


def _synthetic_dataset(tmp_path, n_tasks=6):
    """Enough rows to clear run()'s minimum-size guard, with an
    unambiguous, learnable pattern (easy -> fast wins, hard -> accurate
    wins) so this test isn't relying on the small real dataset.
    """
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    rows = []
    for i in range(n_tasks):
        task_id = f"math-{i:03d}"
        difficulty = "easy" if i % 2 == 0 else "hard"
        _write_task(tasks_dir, task_id, "math", difficulty=difficulty)
        if difficulty == "easy":
            rows.append(
                {
                    "task_id": task_id,
                    "model_config_id": "mock-fast-v1",
                    "status": "success",
                    "evaluation_status": "correct",
                    "estimated_cost_usd": 0.0001,
                }
            )
            rows.append(
                {
                    "task_id": task_id,
                    "model_config_id": "mock-accurate-v1",
                    "status": "success",
                    "evaluation_status": "correct",
                    "estimated_cost_usd": 0.01,
                }
            )
        else:
            rows.append(
                {
                    "task_id": task_id,
                    "model_config_id": "mock-fast-v1",
                    "status": "success",
                    "evaluation_status": "incorrect",
                    "estimated_cost_usd": 0.0001,
                }
            )
            rows.append(
                {
                    "task_id": task_id,
                    "model_config_id": "mock-accurate-v1",
                    "status": "success",
                    "evaluation_status": "correct",
                    "estimated_cost_usd": 0.01,
                }
            )
    results_path = tmp_path / "results.json"
    _write_results(results_path, rows)
    return tasks_dir, results_path


def test_run_refuses_a_too_small_dataset(tmp_path):
    tasks_dir, results_path = _synthetic_dataset(tmp_path, n_tasks=2)
    with pytest.raises(RuntimeError, match="refusing to train"):
        train_module.run(
            result_files=[results_path],
            benchmarks_dir=tasks_dir,
            artifact_path=tmp_path / "artifact.joblib",
            manifest_path=tmp_path / "manifest.json",
        )


def test_run_produces_manifest_with_all_baselines_and_a_loadable_artifact(tmp_path):
    tasks_dir, results_path = _synthetic_dataset(tmp_path, n_tasks=6)
    artifact_path = tmp_path / "artifact.joblib"
    manifest_path = tmp_path / "manifest.json"

    manifest = train_module.run(
        result_files=[results_path],
        benchmarks_dir=tasks_dir,
        artifact_path=artifact_path,
        manifest_path=manifest_path,
    )

    assert manifest["n_training_rows"] == 6
    strategies = {c["strategy"] for c in manifest["comparison"]}
    assert strategies == {"learned-v1", "always-cheapest", "always-strongest", "v2", "random"}
    for entry in manifest["comparison"]:
        assert entry["accuracy_on_evaluable"] is None or 0.0 <= entry["accuracy_on_evaluable"] <= 1.0

    assert artifact_path.exists()
    assert manifest_path.exists()
    loaded = joblib.load(artifact_path)
    assert hasattr(loaded, "predict")


def test_learned_v1_recovers_the_unambiguous_synthetic_pattern(tmp_path):
    """Sanity check on the pipeline mechanics, not a claim about the real
    (much noisier) dataset: when the pattern is genuinely learnable
    (easy -> cheap, hard -> accurate, no exceptions), leave-one-out
    accuracy should be high. This is what distinguishes 'the pipeline is
    broken' from 'the real data doesn't support a good model' — the real
    dataset's poor LOOCV accuracy (see EXPERIMENTS.md) is a data problem,
    verified here to not also be a pipeline bug.
    """
    tasks_dir, results_path = _synthetic_dataset(tmp_path, n_tasks=12)
    manifest = train_module.run(
        result_files=[results_path],
        benchmarks_dir=tasks_dir,
        artifact_path=tmp_path / "artifact.joblib",
        manifest_path=tmp_path / "manifest.json",
    )
    learned = next(c for c in manifest["comparison"] if c["strategy"] == "learned-v1")
    assert learned["accuracy_on_evaluable"] >= 0.9
