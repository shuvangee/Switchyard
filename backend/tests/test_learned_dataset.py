import json
from pathlib import Path

from app.routing.learned.dataset import build_training_rows


def _write_task(dir_: Path, task_id: str, category: str, evaluation_type: str, expected_output=None) -> None:
    (dir_ / f"{task_id}.json").write_text(
        json.dumps(
            {
                "id": task_id,
                "title": task_id,
                "category": category,
                "difficulty": "easy",
                "prompt": f"prompt for {task_id}",
                "evaluation_type": evaluation_type,
                "expected_output": expected_output,
                "metadata": {},
            }
        )
    )


def _write_results(path: Path, executions: list[dict]) -> None:
    path.write_text(json.dumps({"executions": executions}))


def test_manual_eval_tasks_produce_no_rows(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "manual-001", "coding", "manual")

    results_path = tmp_path / "results.json"
    _write_results(
        results_path,
        [
            {
                "task_id": "manual-001",
                "model_config_id": "mock-fast-v1",
                "status": "success",
                "evaluation_status": "not_evaluated",
                "estimated_cost_usd": 0.001,
            }
        ],
    )

    rows, excluded = build_training_rows(result_files=[results_path], benchmarks_dir=tasks_dir)
    assert rows == []
    assert excluded["manual_eval_type"] == 1


def test_task_with_no_correct_candidate_is_excluded(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "math-001", "math", "exact_match", expected_output="7")

    results_path = tmp_path / "results.json"
    _write_results(
        results_path,
        [
            {
                "task_id": "math-001",
                "model_config_id": "mock-fast-v1",
                "status": "success",
                "evaluation_status": "incorrect",
                "estimated_cost_usd": 0.001,
            },
            {
                "task_id": "math-001",
                "model_config_id": "mock-accurate-v1",
                "status": "error",
                "evaluation_status": "not_evaluated",
                "estimated_cost_usd": None,
            },
        ],
    )

    rows, excluded = build_training_rows(result_files=[results_path], benchmarks_dir=tasks_dir)
    assert rows == []
    assert excluded["no_correct_candidate"] == 1


def test_target_is_the_cheapest_correct_candidate(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "math-001", "math", "exact_match", expected_output="7")

    results_path = tmp_path / "results.json"
    _write_results(
        results_path,
        [
            {
                "task_id": "math-001",
                "model_config_id": "mock-accurate-v1",
                "status": "success",
                "evaluation_status": "correct",
                "estimated_cost_usd": 0.01,
            },
            {
                "task_id": "math-001",
                "model_config_id": "mock-fast-v1",
                "status": "success",
                "evaluation_status": "correct",
                "estimated_cost_usd": 0.0001,
            },
        ],
    )

    rows, excluded = build_training_rows(result_files=[results_path], benchmarks_dir=tasks_dir)
    assert len(rows) == 1
    assert rows[0].target_model_id == "mock-fast-v1"  # cheaper of the two correct candidates
    assert excluded["no_correct_candidate"] == 0


def test_incorrect_cheaper_candidate_does_not_win_over_correct_pricier_one(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "math-001", "math", "exact_match", expected_output="7")

    results_path = tmp_path / "results.json"
    _write_results(
        results_path,
        [
            {
                "task_id": "math-001",
                "model_config_id": "mock-fast-v1",
                "status": "success",
                "evaluation_status": "incorrect",
                "estimated_cost_usd": 0.0001,
            },
            {
                "task_id": "math-001",
                "model_config_id": "mock-accurate-v1",
                "status": "success",
                "evaluation_status": "correct",
                "estimated_cost_usd": 0.01,
            },
        ],
    )

    rows, _ = build_training_rows(result_files=[results_path], benchmarks_dir=tasks_dir)
    assert rows[0].target_model_id == "mock-accurate-v1"  # only correct candidate, despite cost


def test_real_project_data_produces_the_expected_row_count():
    """Regression check against the actual committed experiment data —
    catches silent dataset drift (e.g. a new benchmark task file added
    without updating this expectation).
    """
    rows, excluded = build_training_rows()
    assert len(rows) == 24
    assert excluded["manual_eval_type"] == 20
