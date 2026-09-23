"""Applies the sandboxed code-execution grader's results to the 18
coding/debugging (009-013) tasks' evaluation_status in
experiments/results/groq-gpt-oss-expansion.json.

This is an evaluation-quality fix, not a training-pipeline change: it
only corrects evaluation_status from "not_evaluated" to "correct"/
"incorrect" for tasks that now have real ground truth via
backend/app/evaluation/sandbox.py. It does NOT touch each task's
evaluation_type in benchmarks/tasks/*.json (still "manual"), so
backend/app/routing/learned/dataset.py's row-generation gate is
unaffected - these tasks still contribute zero V3 training rows until
that separate, deliberate wiring decision is made.

Re-runs the grader fresh against experiments/results/groq-code-
responses.json rather than hardcoding the last-known 36/36 result, so
this stays correct if either input file changes.

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/apply_code_grading_results.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.evaluation.sandbox import grade_response, is_sandbox_available  # noqa: E402
from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402

FUNCTION_NAMES = {
    "coding-001": "factorial",
    "coding-002": "is_even",
    "coding-003": "reverse_string",
    "coding-004": "is_palindrome",
    "coding-005": "unique_items",
    "coding-006": "sum_of_digits",
    "coding-007": "is_prime",
    "coding-008": "flatten",
    "coding-009": "group_anagrams",
    "coding-010": "longest_increasing_run",
    "coding-011": "merge_dicts",
    "coding-012": "is_balanced",
    "coding-013": "count_vowels",
    "debugging-009": "is_anagram",
    "debugging-010": "running_total",
    "debugging-011": "remove_vowels",
    "debugging-012": "is_power_of_two",
    "debugging-013": "to_dict",
}

REPO_ROOT = Path(__file__).resolve().parents[1]
RESPONSES_PATH = REPO_ROOT / "experiments" / "results" / "groq-code-responses.json"
TARGET_PATH = REPO_ROOT / "experiments" / "results" / "groq-gpt-oss-expansion.json"


def main() -> None:
    if not is_sandbox_available():
        raise SystemExit("sandbox isolation not available - refusing to run untrusted code without it.")
    if not RESPONSES_PATH.exists():
        raise SystemExit(f"{RESPONSES_PATH} not found - run scripts/export_groq_code_responses.py first.")

    responses = {
        (r["task_id"], r["model_config_id"]): r
        for r in json.loads(RESPONSES_PATH.read_text())["executions"]
    }
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}
    target = json.loads(TARGET_PATH.read_text())

    updated = 0
    results_by_key = {}
    for task_id, function_name in FUNCTION_NAMES.items():
        task = tasks[task_id]
        test_cases = task.metadata["test_cases"]
        for model_id in ("groq-gpt-oss-20b", "groq-gpt-oss-120b"):
            record = responses.get((task_id, model_id))
            if record is None or record["status"] != "success" or not record.get("response_text"):
                continue
            grade = grade_response(record["response_text"], function_name, test_cases)
            n_passed = sum(1 for r in grade.test_case_results if r.passed)
            n_total = len(grade.test_case_results)
            results_by_key[(task_id, model_id)] = (grade.all_passed, n_passed, n_total, grade.code_extracted)

    for execution in target["executions"]:
        key = (execution["task_id"], execution["model_config_id"])
        if key not in results_by_key:
            continue
        all_passed, n_passed, n_total, code_extracted = results_by_key[key]
        execution["evaluation_status"] = "correct" if all_passed else "incorrect"
        if not code_extracted:
            execution["evaluation_detail"] = "code_execution: no fenced code block found"
        else:
            execution["evaluation_detail"] = f"code_execution: {n_passed}/{n_total} test cases passed"
        updated += 1

    TARGET_PATH.write_text(json.dumps(target, indent=2) + "\n")
    print(f"updated {updated} execution(s) in {TARGET_PATH.relative_to(REPO_ROOT)}")

    passed = sum(1 for v in results_by_key.values() if v[0])
    print(f"{passed}/{len(results_by_key)} (task, model) pairs graded as correct")
    if passed != len(results_by_key):
        for (task_id, model_id), (all_passed, n_passed, n_total, _) in sorted(results_by_key.items()):
            if not all_passed:
                print(f"  INCORRECT: {task_id} / {model_id} ({n_passed}/{n_total} test cases)")


if __name__ == "__main__":
    main()
