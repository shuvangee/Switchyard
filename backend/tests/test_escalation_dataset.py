import json

from app.routing.learned.escalation_dataset import (
    MODEL_120B_ID,
    MODEL_20B_ID,
    build_escalation_rows,
)


def _write_task(dir_, task_id, category="summarization", evaluation_type="valid_json"):
    (dir_ / f"{task_id}.json").write_text(
        json.dumps(
            {
                "id": task_id,
                "title": task_id,
                "category": category,
                "difficulty": "medium",
                "prompt": f"Prompt for {task_id}.",
                "evaluation_type": evaluation_type,
                "expected_output": "x",
                "metadata": {},
            }
        )
    )


def _execution(task_id, model_id, evaluation_status, latency=100.0, cost=0.001):
    return {
        "task_id": task_id,
        "model_config_id": model_id,
        "status": "success",
        "evaluation_status": evaluation_status,
        "latency_ms": latency,
        "estimated_cost_usd": cost,
    }


def test_only_120b_correct_produces_escalate_true(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "task-001")
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "executions": [
                    _execution("task-001", MODEL_20B_ID, "incorrect"),
                    _execution("task-001", MODEL_120B_ID, "correct"),
                ]
            }
        )
    )

    rows, excluded = build_escalation_rows(results_path=results_path, benchmarks_dir=tasks_dir)

    assert len(rows) == 1
    assert rows[0].escalate is True
    assert rows[0].correct_20b is False
    assert rows[0].correct_120b is True
    assert excluded == {"no_ground_truth_for_both_models": 0}


def test_both_correct_produces_escalate_false(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "task-001")
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "executions": [
                    _execution("task-001", MODEL_20B_ID, "correct"),
                    _execution("task-001", MODEL_120B_ID, "correct"),
                ]
            }
        )
    )

    rows, _ = build_escalation_rows(results_path=results_path, benchmarks_dir=tasks_dir)
    assert rows[0].escalate is False


def test_only_20b_correct_produces_escalate_false(tmp_path):
    """120b would be the WRONG choice here - escalating is never labeled
    correct just because the model differs from 20b."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "task-001")
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "executions": [
                    _execution("task-001", MODEL_20B_ID, "correct"),
                    _execution("task-001", MODEL_120B_ID, "incorrect"),
                ]
            }
        )
    )
    rows, _ = build_escalation_rows(results_path=results_path, benchmarks_dir=tasks_dir)
    assert rows[0].escalate is False


def test_both_incorrect_produces_escalate_false_not_excluded(tmp_path):
    """Escalating buys nothing when both models are wrong - the row still
    gets a label (don't pay for 120b when it wouldn't help either), it is
    not silently dropped the way a task with NO ground truth is."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "task-001")
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "executions": [
                    _execution("task-001", MODEL_20B_ID, "incorrect"),
                    _execution("task-001", MODEL_120B_ID, "incorrect"),
                ]
            }
        )
    )

    rows, excluded = build_escalation_rows(results_path=results_path, benchmarks_dir=tasks_dir)
    assert len(rows) == 1
    assert rows[0].escalate is False
    assert excluded["no_ground_truth_for_both_models"] == 0


def test_task_missing_one_models_execution_is_excluded_not_guessed(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "task-001")
    _write_task(tasks_dir, "task-002")
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "executions": [
                    _execution("task-001", MODEL_20B_ID, "correct"),
                    _execution("task-001", MODEL_120B_ID, "correct"),
                    _execution("task-002", MODEL_20B_ID, "correct"),
                    # task-002 has no 120b execution at all
                ]
            }
        )
    )

    rows, excluded = build_escalation_rows(results_path=results_path, benchmarks_dir=tasks_dir)
    assert len(rows) == 1
    assert rows[0].task_id == "task-001"
    assert excluded["no_ground_truth_for_both_models"] == 1


def test_manual_only_task_is_excluded_not_guessed(tmp_path):
    """A task with no recorded execution at all for either model (the
    real shape of the 12 manual-only benchmark tasks) contributes no row."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "task-001", evaluation_type="manual")
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps({"executions": []}))

    rows, excluded = build_escalation_rows(results_path=results_path, benchmarks_dir=tasks_dir)
    assert rows == []
    assert excluded["no_ground_truth_for_both_models"] == 1


def test_not_evaluated_status_is_excluded_not_treated_as_incorrect(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "task-001")
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "executions": [
                    _execution("task-001", MODEL_20B_ID, "not_evaluated"),
                    _execution("task-001", MODEL_120B_ID, "correct"),
                ]
            }
        )
    )

    rows, excluded = build_escalation_rows(results_path=results_path, benchmarks_dir=tasks_dir)
    assert rows == []
    assert excluded["no_ground_truth_for_both_models"] == 1


def test_real_project_data_produces_92_rows_with_5_positive_labels():
    """Regression check against the actual committed groq-gpt-oss-
    expansion.json - catches silent drift the same way
    test_learned_dataset.py's real-data test does for the original
    dataset. 92 = the real evaluation-coverage number (see
    experiments/results/evaluation-coverage-report.md); 5 = only-120b-
    correct tasks (see experiments/results/routing-opportunity-
    analysis.md's disagreement breakdown)."""
    rows, excluded = build_escalation_rows()
    assert len(rows) == 92
    assert excluded == {"no_ground_truth_for_both_models": 12}
    assert sum(row.escalate for row in rows) == 5
