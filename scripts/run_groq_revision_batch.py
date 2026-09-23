"""Runs ONLY the 9 tasks whose prompts were revised in V2.6 Phase 1
(debugging-001 through 008, reasoning-005) against both Groq models -
their original responses don't match the revised prompts, so this is
the one batch that genuinely needs a NEW call rather than an export of
existing data.

9 tasks x 2 models = 18 requests total. Free tier, well under 1,000
requests/day/model - no cost. Does NOT touch the other 95 tasks or
re-run anything already graded.

Writes to a SEPARATE results file (groq-revision-batch.json), not
directly into groq-gpt-oss-expansion.json, so a partial or bad run
can't corrupt the canonical results file - merge happens as a
reviewed, separate step after this completes.

Requires GROQ_API_KEY set (backend/.env).

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/run_groq_revision_batch.py
"""

import json
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.core.time import utcnow  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.experiments.loader import (  # noqa: E402
    default_benchmarks_dir,
    load_benchmark_tasks,
    sync_benchmark_tasks,
)
from app.experiments.runner import execute_single  # noqa: E402
from app.models.benchmark import BenchmarkTaskORM  # noqa: E402
from app.models.enums import RunStatus  # noqa: E402
from app.models.experiment import ExperimentRunORM  # noqa: E402
from app.models.model_config import ModelConfigORM  # noqa: E402
from app.providers.registry import sync_model_configs  # noqa: E402

TASK_IDS = [f"debugging-{i:03d}" for i in range(1, 9)] + ["reasoning-005"]
MODEL_CONFIG_IDS = ["groq-gpt-oss-20b", "groq-gpt-oss-120b"]
RESULTS_FILENAME = "groq-revision-batch.json"
REQUEST_PACING_SECONDS = 2.5
RETRY_BACKOFF_SECONDS = 45


def _to_record(execution, task) -> dict:
    return {
        "task_id": execution.task_id,
        "category": task.category,
        "difficulty": task.difficulty,
        "evaluation_type": task.evaluation_type,
        "model_config_id": execution.model_config_id,
        "status": execution.status,
        "response_text": execution.response_text,
        "latency_ms": execution.latency_ms,
        "input_tokens": execution.input_tokens,
        "output_tokens": execution.output_tokens,
        "estimated_cost_usd": execution.estimated_cost_usd,
        "evaluation_status": execution.evaluation_status,
        "error_message": execution.error_message,
    }


def main() -> None:
    settings = get_settings()
    if not settings.groq_api_key:
        raise SystemExit("GROQ_API_KEY is not set (backend/.env) — aborting before any call.")

    init_db(engine)
    session = SessionLocal()

    tasks = load_benchmark_tasks(default_benchmarks_dir())
    sync_benchmark_tasks(session, tasks)
    sync_model_configs(session)

    task_orms = session.query(BenchmarkTaskORM).filter(BenchmarkTaskORM.id.in_(TASK_IDS)).all()
    missing_tasks = set(TASK_IDS) - {t.id for t in task_orms}
    if missing_tasks:
        raise SystemExit(f"unknown task ids (benchmark file missing?): {sorted(missing_tasks)}")
    task_orms.sort(key=lambda t: t.id)

    models = session.query(ModelConfigORM).filter(ModelConfigORM.id.in_(MODEL_CONFIG_IDS)).all()
    disabled = [m.id for m in models if not m.enabled]
    if disabled:
        raise SystemExit(f"model_config ids are disabled (missing key?): {disabled}")
    models.sort(key=lambda m: m.id)

    run = ExperimentRunORM(
        id=str(uuid4()),
        name="groq-revision-batch",
        status=RunStatus.RUNNING.value,
        task_ids=TASK_IDS,
        model_config_ids=MODEL_CONFIG_IDS,
        created_at=utcnow(),
        completed_at=None,
    )
    session.add(run)
    session.commit()

    results_path = Path(__file__).resolve().parents[1] / "experiments" / "results" / RESULTS_FILENAME
    results_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    counts = {m.id: {"success": 0, "error": 0} for m in models}
    errors: list[dict] = []

    def save() -> None:
        output = {
            "run_id": run.id,
            "created_at": run.created_at.isoformat(),
            "provider_note": (
                "V2.6 Phase 1 revision batch: only the 9 tasks whose prompts "
                "changed (debugging-001-008, reasoning-005) - free tier, no "
                "payment method on the account"
            ),
            "task_count": len(task_orms),
            "model_ids": MODEL_CONFIG_IDS,
            "executions": records,
        }
        results_path.write_text(json.dumps(output, indent=2) + "\n")

    def run_pass(pending: list[tuple], label: str) -> list[tuple]:
        still_failing = []
        for task, model in pending:
            execution = execute_single(task, model)
            execution.run_id = run.id
            session.add(execution)
            session.commit()

            rec = _to_record(execution, task)
            records[:] = [
                r for r in records
                if not (r["task_id"] == rec["task_id"] and r["model_config_id"] == rec["model_config_id"])
            ]
            records.append(rec)
            save()

            if execution.status == "success":
                counts[model.id]["success"] += 1
            else:
                counts[model.id]["error"] += 1
                print(f"[{label}] ERROR {task.id} / {model.id}: {execution.error_message}")
                still_failing.append((task, model))
                errors.append({"task_id": task.id, "model_config_id": model.id, "error": execution.error_message})
                continue
            time.sleep(REQUEST_PACING_SECONDS)
        return still_failing

    pending = [(task, model) for task in task_orms for model in models]
    print(f"running {len(pending)} (task, model) calls against {MODEL_CONFIG_IDS}...")
    still_failing = run_pass(pending, "pass 1")

    if still_failing:
        print(f"\n{len(still_failing)} call(s) failed on pass 1 — waiting {RETRY_BACKOFF_SECONDS}s, then retrying once...")
        time.sleep(RETRY_BACKOFF_SECONDS)
        for task, model in still_failing:
            counts[model.id]["error"] -= 1
        errors[:] = [
            e for e in errors
            if (e["task_id"], e["model_config_id"]) not in {(t.id, m.id) for t, m in still_failing}
        ]
        still_failing = run_pass(still_failing, "retry")

    run.status = RunStatus.COMPLETED.value
    run.completed_at = utcnow()
    session.commit()

    total_cost = sum(r["estimated_cost_usd"] for r in records if r["estimated_cost_usd"])
    print(f"\nwrote {results_path.relative_to(Path(__file__).resolve().parents[1])}\n")
    for model_id, c in counts.items():
        print(f"{model_id}: {c['success']} succeeded, {c['error']} failed")
    if errors:
        print("\nunresolved errors:")
        for e in errors:
            print(f"  {e['task_id']} / {e['model_config_id']}: {e['error']}")
    print(f"\ntotal estimated cost (notional, not billed — free tier, no payment method): ${total_cost:.6f}")


if __name__ == "__main__":
    main()
