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

    2026-09-23: wired in experiments/results/groq-gpt-oss-expansion.json
    (run from outside this sandbox, since groq.com is blocked here — see
    FAILURES_AND_LESSONS.md) covering all 104 tasks against both Groq
    models, then regenerated v0-mock-baseline.json (free, mock-only)
    against all 104 tasks too, closing the coverage gap that made the
    baseline comparison in train.py apples-to-oranges (see that file's
    _cheapest_and_strongest_model_ids docstring). Row count: 24 -> 55
    (Groq run) -> 56 (mock regeneration recovers one of the two tasks
    neither Groq model got right — classification-010 or math-013, now
    answered correctly by a mock candidate). no_executions is 0 since
    every task now has at least one real or mock execution recorded.

    2026-09-23 (V2.6 evaluation-coverage pass): reasoning-001/002/003
    converted from manual to exact_match, then reasoning-005 too (prompt
    narrowed to ask for oranges only - see benchmarks/tasks/). All 4 were
    briefly a TRANSIENT state (real scores not applied yet), tracked as
    manual_eval_type: 47 -> 43 (-4); no_correct_candidate: 1 -> 5 (+4).

    2026-09-24 (V2.6 Phase A/B applied): real scores now exist for all 4 -
    reasoning-001/002/003 rescored via export_original_run_extras.py +
    apply_remaining_grading_results.py (no new call, prompts unchanged);
    reasoning-005 via an actual new Groq call (run_groq_revision_batch.py
    + apply_revision_batch_results.py, prompt was revised). 3 of the 4
    now have a real correct candidate and produce a training row;
    reasoning-003 does not (both Groq models score it incorrect, and its
    mock/gemini executions predate its exact_match conversion so they're
    still not_evaluated - a real, verified "no correct candidate", not a
    gap). no_correct_candidate: 5 -> 2, leaving exactly math-013 (pre-
    existing, unrelated to this pass) and reasoning-003. rows: 56 -> 59.

    NOTE: debugging-001-008 and the 6 auto-gradeable summarization tasks
    were ALSO scored this pass (real evaluation_status, feeding the
    evaluation-coverage report and routing-opportunity analysis), but
    their evaluation_type stays "manual" by design (sandbox/required-
    facts grading is deliberately NOT wired into EvaluationType - see
    backend/app/evaluation/sandbox.py) - so build_training_rows()
    excludes them via manual_eval_type exactly as before. manual_eval_type
    stays 43; scoring them did not and was not meant to change this
    number.
    """
    rows, excluded = build_training_rows()
    assert len(rows) == 59
    assert excluded["manual_eval_type"] == 43
    assert excluded["no_executions"] == 0
    assert excluded["no_correct_candidate"] == 2
