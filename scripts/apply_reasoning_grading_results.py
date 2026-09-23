"""Rescores reasoning-001/002/003 in experiments/results/groq-gpt-oss-
expansion.json using the existing exact_match evaluator, against
response_text exported from the local database (no new API calls,
mirrors apply_code_grading_results.py).

Requires experiments/results/groq-reasoning-responses.json - produced
by scripts/export_reasoning_responses.py.

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/apply_reasoning_grading_results.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.evaluation.strategies import evaluate  # noqa: E402
from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402
from app.models.enums import EvaluationType  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RESPONSES_PATH = REPO_ROOT / "experiments" / "results" / "groq-reasoning-responses.json"
TARGET_PATH = REPO_ROOT / "experiments" / "results" / "groq-gpt-oss-expansion.json"
TASK_IDS = ["reasoning-001", "reasoning-002", "reasoning-003"]


def main() -> None:
    if not RESPONSES_PATH.exists():
        raise SystemExit(f"{RESPONSES_PATH} not found - run scripts/export_reasoning_responses.py first.")

    responses = {
        (r["task_id"], r["model_config_id"]): r
        for r in json.loads(RESPONSES_PATH.read_text())["executions"]
    }
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}
    target = json.loads(TARGET_PATH.read_text())

    updated = 0
    for execution in target["executions"]:
        key = (execution["task_id"], execution["model_config_id"])
        if execution["task_id"] not in TASK_IDS or key not in responses:
            continue
        record = responses[key]
        if record["status"] != "success" or not record.get("response_text"):
            continue
        task = tasks[execution["task_id"]]
        outcome = evaluate(EvaluationType(task.evaluation_type.value), record["response_text"], task.expected_output)
        execution["evaluation_status"] = outcome.status.value
        if outcome.detail:
            execution["evaluation_detail"] = outcome.detail
        updated += 1
        print(f"{execution['task_id']} / {execution['model_config_id']}: {outcome.status.value}")

    TARGET_PATH.write_text(json.dumps(target, indent=2) + "\n")
    print(f"\nupdated {updated} execution(s) in {TARGET_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
