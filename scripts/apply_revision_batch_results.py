"""Applies scripts/run_groq_revision_batch.py's results into
experiments/results/groq-gpt-oss-expansion.json - the 7 gradeable
debugging tasks (001-006, 008; NOT 007, which stays manual) via the
sandboxed code-execution grader, and reasoning-005 via exact_match.

Requires experiments/results/groq-revision-batch.json - produced by
scripts/run_groq_revision_batch.py.

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/apply_revision_batch_results.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.evaluation.sandbox import grade_response  # noqa: E402
from app.evaluation.strategies import evaluate  # noqa: E402
from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402
from app.models.enums import EvaluationType  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = REPO_ROOT / "experiments" / "results" / "groq-revision-batch.json"
TARGET_PATH = REPO_ROOT / "experiments" / "results" / "groq-gpt-oss-expansion.json"

DEBUGGING_FUNCTION_NAMES = {
    "debugging-001": "total",
    "debugging-002": "average",
    "debugging-003": "double_all",
    "debugging-004": "dedupe",
    "debugging-005": "find_max",
    "debugging-006": "is_empty",
    "debugging-008": "title_case",
}


def main() -> None:
    if not BATCH_PATH.exists():
        raise SystemExit(f"{BATCH_PATH} not found - run scripts/run_groq_revision_batch.py first.")

    batch = {
        (r["task_id"], r["model_config_id"]): r
        for r in json.loads(BATCH_PATH.read_text())["executions"]
    }
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}
    target = json.loads(TARGET_PATH.read_text())

    updated = 0
    for execution in target["executions"]:
        task_id = execution["task_id"]
        key = (task_id, execution["model_config_id"])
        if key not in batch:
            continue
        record = batch[key]
        if record["status"] != "success" or not record.get("response_text"):
            continue
        task = tasks[task_id]

        if task_id in DEBUGGING_FUNCTION_NAMES:
            function_name = DEBUGGING_FUNCTION_NAMES[task_id]
            test_cases = task.metadata["test_cases"]
            grade = grade_response(record["response_text"], function_name, test_cases)
            execution["evaluation_status"] = "correct" if grade.all_passed else "incorrect"
            n_passed = sum(1 for r in grade.test_case_results if r.passed)
            n_total = len(grade.test_case_results)
            execution["evaluation_detail"] = (
                f"code_execution: {n_passed}/{n_total} test cases passed"
                if grade.code_extracted
                else "code_execution: no fenced code block found"
            )
            updated += 1
            print(f"{task_id} / {execution['model_config_id']}: {execution['evaluation_status']}")
        elif task_id == "reasoning-005":
            outcome = evaluate(EvaluationType(task.evaluation_type.value), record["response_text"], task.expected_output)
            execution["evaluation_status"] = outcome.status.value
            if outcome.detail:
                execution["evaluation_detail"] = outcome.detail
            updated += 1
            print(f"{task_id} / {execution['model_config_id']}: {outcome.status.value}")
        # debugging-007 is intentionally excluded - stays manual, see its
        # own metadata.deterministic_grading_attempted_and_rejected.

    TARGET_PATH.write_text(json.dumps(target, indent=2) + "\n")
    print(f"\nupdated {updated} execution(s) in {TARGET_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
