"""Report-only: grades the 13 coding + 5 revised debugging (009-013)
tasks' Groq responses via the sandboxed code-execution grader.

Does NOT wire results into the training pipeline (backend/app/routing/
learned/dataset.py) - that is a deliberate follow-up decision, not made
here. This script only extracts, runs, and reports pass/fail.

Input: experiments/results/groq-code-responses.json, produced by
scripts/export_groq_code_responses.py (response_text was never captured
in groq-gpt-oss-expansion.json itself - see FAILURES_AND_LESSONS.md).

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/grade_code_responses.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.evaluation.sandbox import grade_response, is_sandbox_available  # noqa: E402
from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402

# Task id -> the function name each prompt asks the model to define.
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

RESPONSES_PATH = Path(__file__).resolve().parents[1] / "experiments" / "results" / "groq-code-responses.json"


def main() -> None:
    if not is_sandbox_available():
        raise SystemExit(
            "sandbox isolation (unshare --mount --net) is not available in this "
            "environment - refusing to run untrusted code without it."
        )
    if not RESPONSES_PATH.exists():
        raise SystemExit(
            f"{RESPONSES_PATH.relative_to(RESPONSES_PATH.parents[2])} not found - "
            "run scripts/export_groq_code_responses.py first (see that script's "
            "docstring)."
        )

    responses = json.loads(RESPONSES_PATH.read_text())["executions"]
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}

    print(f"{'task_id':<16}{'model':<22}{'code_found':<12}{'result':<10}{'test_cases'}")
    print("-" * 90)

    summary: dict[str, dict[str, str]] = {}
    for record in responses:
        task_id = record["task_id"]
        model_id = record["model_config_id"]
        task = tasks[task_id]
        function_name = FUNCTION_NAMES[task_id]
        test_cases = task.metadata["test_cases"]

        if record["status"] != "success" or not record.get("response_text"):
            summary.setdefault(task_id, {})[model_id] = "no_response"
            print(f"{task_id:<16}{model_id:<22}{'n/a':<12}{'no_response':<10}")
            continue

        grade = grade_response(record["response_text"], function_name, test_cases)
        outcome = "PASS" if grade.all_passed else ("FAIL" if grade.code_extracted else "NO_CODE")
        summary.setdefault(task_id, {})[model_id] = outcome

        per_case = "".join("P" if r.passed else "F" for r in grade.test_case_results) or "-"
        print(f"{task_id:<16}{model_id:<22}{str(grade.code_extracted):<12}{outcome:<10}{per_case}")

    print()
    print("summary (per task, both models must PASS for either row count to change downstream):")
    for task_id in FUNCTION_NAMES:
        results = summary.get(task_id, {})
        print(f"  {task_id:<16} " + "  ".join(f"{m}={results.get(m, 'missing')}" for m in ("groq-gpt-oss-20b", "groq-gpt-oss-120b")))

    total = sum(len(v) for v in summary.values())
    passed = sum(1 for v in summary.values() for outcome in v.values() if outcome == "PASS")
    print(f"\n{passed}/{total} (task, model) pairs passed all test cases")


if __name__ == "__main__":
    main()
