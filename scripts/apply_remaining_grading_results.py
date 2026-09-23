"""Rescores every task exported by scripts/export_original_run_extras.py
against experiments/results/groq-gpt-oss-expansion.json - reasoning-
001/002/003 via the existing exact_match evaluator, and the 6 auto-
gradeable summarization tasks (005/006/007/008/010/013) via the new
required_facts checker. No new API calls; no new evaluation
infrastructure beyond what already exists.

The 7 manual summarization tasks are NOT auto-scored here (by design -
see their metadata.grading_method) but their real response_text is
still available in the export for a human doing that manual review.

Requires experiments/results/groq-remaining-responses.json - produced
by scripts/export_original_run_extras.py.

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/apply_remaining_grading_results.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.evaluation.required_facts import check_required_facts  # noqa: E402
from app.evaluation.strategies import evaluate  # noqa: E402
from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402
from app.models.enums import EvaluationType  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RESPONSES_PATH = REPO_ROOT / "experiments" / "results" / "groq-remaining-responses.json"
TARGET_PATH = REPO_ROOT / "experiments" / "results" / "groq-gpt-oss-expansion.json"

REASONING_EXACT_MATCH_TASKS = ["reasoning-001", "reasoning-002", "reasoning-003"]
SUMMARIZATION_REQUIRED_FACTS_TASKS = [
    "summarization-005",
    "summarization-006",
    "summarization-007",
    "summarization-008",
    "summarization-010",
    "summarization-013",
]


def main() -> None:
    if not RESPONSES_PATH.exists():
        raise SystemExit(f"{RESPONSES_PATH} not found - run scripts/export_original_run_extras.py first.")

    responses = {
        (r["task_id"], r["model_config_id"]): r
        for r in json.loads(RESPONSES_PATH.read_text())["executions"]
    }
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}
    target = json.loads(TARGET_PATH.read_text())

    updated = 0
    for execution in target["executions"]:
        task_id = execution["task_id"]
        key = (task_id, execution["model_config_id"])
        if key not in responses:
            continue
        record = responses[key]
        if record["status"] != "success" or not record.get("response_text"):
            continue
        task = tasks[task_id]

        if task_id in REASONING_EXACT_MATCH_TASKS:
            outcome = evaluate(EvaluationType(task.evaluation_type.value), record["response_text"], task.expected_output)
            execution["evaluation_status"] = outcome.status.value
            if outcome.detail:
                execution["evaluation_detail"] = outcome.detail
            updated += 1
            print(f"{task_id} / {execution['model_config_id']}: {outcome.status.value}")
        elif task_id in SUMMARIZATION_REQUIRED_FACTS_TASKS:
            required = task.metadata["required_facts"]
            ok, missing = check_required_facts(record["response_text"], required)
            execution["evaluation_status"] = "correct" if ok else "incorrect"
            execution["evaluation_detail"] = (
                "all required facts present" if ok else f"missing required fact(s): {missing}"
            )
            updated += 1
            print(f"{task_id} / {execution['model_config_id']}: {execution['evaluation_status']}")
        # Manual summarization tasks: response_text is in the export for
        # human review, but evaluation_status is intentionally left
        # untouched here - no automated grading claim is made for them.

    TARGET_PATH.write_text(json.dumps(target, indent=2) + "\n")
    print(f"\nupdated {updated} execution(s) in {TARGET_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
