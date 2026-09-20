"""Run the 12 benchmark tasks against ONE real provider: Gemini.

This is Switchyard's first experiment against a real (non-mock) model.
Unlike run_v0_baseline.py (which runs every enabled model, mock included),
this script runs exactly one model_config_id so the resulting file is a
clean real-provider record, not mixed in with mock data. Requires
GOOGLE_API_KEY set (backend/.env) and costs real money, though at this
scale (12 short prompts, output capped at 512 tokens/call) it is a
fraction of a cent — see docs/case-study/EXPERIMENTS.md for the estimate
made before this was run.

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/run_gemini_baseline.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.experiments.loader import (  # noqa: E402
    default_benchmarks_dir,
    load_benchmark_tasks,
    sync_benchmark_tasks,
)
from app.experiments.runner import run_experiment  # noqa: E402
from app.providers.registry import sync_model_configs  # noqa: E402

MODEL_CONFIG_ID = "gemini-3.6-flash"
RESULTS_FILENAME = "gemini-3.6-flash-baseline.json"
MAX_RETRY_ROUNDS = 2
RETRY_BACKOFF_SECONDS = 20


def _to_record(execution, task_by_id) -> dict:
    task = task_by_id[execution.task_id]
    return {
        "task_id": execution.task_id,
        "category": task.category.value,
        "difficulty": task.difficulty.value,
        "evaluation_type": task.evaluation_type.value,
        "model_config_id": execution.model_config_id,
        "status": execution.status,
        "latency_ms": execution.latency_ms,
        "input_tokens": execution.input_tokens,
        "output_tokens": execution.output_tokens,
        "estimated_cost_usd": execution.estimated_cost_usd,
        "evaluation_status": execution.evaluation_status,
        "error_message": execution.error_message,
    }


def main() -> None:
    settings = get_settings()
    if not settings.google_api_key:
        raise SystemExit("GOOGLE_API_KEY is not set (backend/.env) — aborting before any call.")

    init_db(engine)
    session = SessionLocal()

    tasks = load_benchmark_tasks(default_benchmarks_dir())
    sync_benchmark_tasks(session, tasks)
    sync_model_configs(session)
    task_by_id = {t.id: t for t in tasks}

    run = run_experiment(
        session,
        task_ids=[t.id for t in tasks],
        model_config_ids=[MODEL_CONFIG_ID],
        name=f"{MODEL_CONFIG_ID}-baseline",
    )
    records_by_task = {e.task_id: _to_record(e, task_by_id) for e in run.executions}

    # A real provider rate-limits in a way the mock never does — retry only
    # the failed tasks, with backoff, rather than re-spending on every task.
    for round_num in range(1, MAX_RETRY_ROUNDS + 1):
        failed_task_ids = [tid for tid, r in records_by_task.items() if r["status"] != "success"]
        if not failed_task_ids:
            break
        print(f"retry round {round_num}: {len(failed_task_ids)} task(s) failed, waiting {RETRY_BACKOFF_SECONDS}s...")
        time.sleep(RETRY_BACKOFF_SECONDS)
        retry_run = run_experiment(
            session,
            task_ids=failed_task_ids,
            model_config_ids=[MODEL_CONFIG_ID],
            name=f"{MODEL_CONFIG_ID}-baseline-retry-{round_num}",
        )
        for execution in retry_run.executions:
            records_by_task[execution.task_id] = _to_record(execution, task_by_id)

    records = [records_by_task[t.id] for t in tasks]

    output = {
        "run_id": run.id,
        "created_at": run.created_at.isoformat(),
        "provider_note": f"real Gemini API call ({MODEL_CONFIG_ID}) — Switchyard's first real-provider experiment",
        "task_count": len(tasks),
        "model_ids": [MODEL_CONFIG_ID],
        "executions": records,
    }
    results_path = Path(__file__).resolve().parents[1] / "experiments" / "results" / RESULTS_FILENAME
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {results_path.relative_to(Path(__file__).resolve().parents[1])}\n")

    header = f"{'category':<18}{'difficulty':<10}{'status':<22}{'latency_ms':>11}{'cost_usd':>12}{'eval':<12}"
    print(header)
    print("-" * len(header))
    for r in records:
        eval_label = r["evaluation_status"] if r["status"] == "success" else "error"
        latency = f"{r['latency_ms']:.0f}" if r["latency_ms"] is not None else "-"
        cost = f"{r['estimated_cost_usd']:.6f}" if r["estimated_cost_usd"] is not None else "-"
        print(f"{r['category']:<18}{r['difficulty']:<10}{r['status']:<22}{latency:>11}{cost:>12}{eval_label:<12}")

    succeeded = sum(1 for r in records if r["status"] == "success")
    total_cost = sum(r["estimated_cost_usd"] for r in records if r["estimated_cost_usd"])
    total_input = sum(r["input_tokens"] for r in records if r["input_tokens"])
    total_output = sum(r["output_tokens"] for r in records if r["output_tokens"])
    print(f"\nsucceeded: {succeeded}/{len(records)}")
    print(f"total input tokens: {total_input}  total output tokens: {total_output}")
    print(f"total estimated cost: ${total_cost:.6f}")


if __name__ == "__main__":
    main()
