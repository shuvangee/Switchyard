"""Re-score the V0 mock baseline and the first Gemini experiment using the
current (fixed) evaluation strategies, with NO new provider calls.

Mock responses: MockProvider is a deterministic function of (model_id,
prompt) — a SHA256 hash seed, no randomness or time dependency (see
app/providers/mock.py) — so regenerating them reproduces byte-identical
text to the original v0-mock-baseline.json run. This is a pure local
computation, not an API call.

Gemini responses: the actual raw text from the real run, read from the
local dev DB (backend/switchyard.db) where it was persisted when the
experiment ran. No new Gemini call is made.

For every row, compares the evaluation_status already recorded in the
committed results file (the "before" score) against a fresh evaluate()
call using the current strategies.py (the "after" score), and reports
every row where they differ plus a regression check (any row that was
CORRECT before and is not CORRECT now).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.evaluation.strategies import evaluate  # noqa: E402
from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402
from app.models.enums import EvaluationType  # noqa: E402
from app.models.experiment import ExperimentRunORM, ModelExecutionORM  # noqa: E402
from app.providers.registry import get_provider  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def rescore_mock() -> list[dict]:
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}
    old_data = json.loads((REPO_ROOT / "experiments/results/v0-mock-baseline.json").read_text())
    mock_provider = get_provider("mock")

    rows = []
    for old in old_data["executions"]:
        task = tasks[old["task_id"]]
        if old["status"] != "success":
            rows.append({**old, "source": "mock", "new_evaluation_status": old["evaluation_status"]})
            continue
        result = mock_provider.generate(old["model_config_id"], task.prompt)
        outcome = evaluate(EvaluationType(old["evaluation_type"]), result.text, task.expected_output)
        rows.append(
            {
                **old,
                "source": "mock",
                "response_text": result.text,
                "new_evaluation_status": outcome.status.value,
            }
        )
    return rows


def rescore_gemini() -> list[dict]:
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}
    old_data = json.loads((REPO_ROOT / "experiments/results/gemini-3.6-flash-baseline.json").read_text())

    session = SessionLocal()
    runs = session.query(ExperimentRunORM).filter(ExperimentRunORM.name.like("gemini-3.6-flash%")).all()
    run_ids = [r.id for r in runs]
    execs = (
        session.query(ModelExecutionORM)
        .filter(ModelExecutionORM.run_id.in_(run_ids), ModelExecutionORM.status == "success")
        .all()
    )
    response_by_task: dict[str, str] = {}
    for e in execs:
        response_by_task[e.task_id] = e.response_text  # later retries overwrite earlier attempts

    rows = []
    for old in old_data["executions"]:
        task = tasks[old["task_id"]]
        if old["status"] != "success":
            rows.append({**old, "source": "gemini", "new_evaluation_status": old["evaluation_status"]})
            continue
        response_text = response_by_task[old["task_id"]]
        outcome = evaluate(EvaluationType(old["evaluation_type"]), response_text, task.expected_output)
        rows.append(
            {
                **old,
                "source": "gemini",
                "response_text": response_text,
                "new_evaluation_status": outcome.status.value,
            }
        )
    return rows


def main() -> None:
    rows = rescore_mock() + rescore_gemini()

    changed = [r for r in rows if r["evaluation_status"] != r["new_evaluation_status"]]
    regressions = [
        r for r in rows if r["evaluation_status"] == "correct" and r["new_evaluation_status"] != "correct"
    ]

    print(f"{len(rows)} rows checked ({sum(1 for r in rows if r['source']=='mock')} mock, "
          f"{sum(1 for r in rows if r['source']=='gemini')} gemini)\n")

    print(f"{len(changed)} row(s) changed score:")
    for r in changed:
        print(
            f"  [{r['source']}] {r['task_id']:<22} {r['model_config_id']:<20} "
            f"{r['evaluation_status']:<12} -> {r['new_evaluation_status']}"
        )

    print(f"\n{len(regressions)} regression(s) (was correct, now not correct):")
    for r in regressions:
        print(f"  [{r['source']}] {r['task_id']} {r['model_config_id']}")
    if not regressions:
        print("  none")


if __name__ == "__main__":
    main()
