"""Run every enabled model against every benchmark task and report a
per-category/difficulty breakdown.

This is the evidence V1's routing rules (backend/app/routing/rules.py) are
based on. It uses whatever providers are currently enabled in the model
registry — with no OPENAI_API_KEY configured, that means the mock
provider only, so treat this as an illustrative baseline about how the
*system* behaves, not a claim about any real model's performance.

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/run_v0_baseline.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.init_db import init_db  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.experiments.loader import (  # noqa: E402
    default_benchmarks_dir,
    load_benchmark_tasks,
    sync_benchmark_tasks,
)
from app.experiments.runner import run_experiment  # noqa: E402
from app.providers.registry import get_model_registry, sync_model_configs  # noqa: E402


def main() -> None:
    init_db(engine)
    session = SessionLocal()

    tasks = load_benchmark_tasks(default_benchmarks_dir())
    sync_benchmark_tasks(session, tasks)
    sync_model_configs(session)

    models = [m for m in get_model_registry() if m.enabled]
    task_by_id = {t.id: t for t in tasks}

    run = run_experiment(
        session,
        task_ids=[t.id for t in tasks],
        model_config_ids=[m.id for m in models],
        name="v0-baseline",
    )

    records = []
    for execution in run.executions:
        task = task_by_id[execution.task_id]
        records.append(
            {
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
            }
        )

    output = {
        "run_id": run.id,
        "created_at": run.created_at.isoformat(),
        "provider_note": "mock provider only (no OPENAI_API_KEY configured)",
        "task_count": len(tasks),
        "model_ids": [m.id for m in models],
        "executions": records,
    }
    results_path = Path(__file__).resolve().parents[1] / "experiments" / "results" / "v0-mock-baseline.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {results_path.relative_to(Path(__file__).resolve().parents[1])}\n")

    # --- per (category, difficulty, model) summary ---
    by_key: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in records:
        by_key[(r["category"], r["difficulty"], r["model_config_id"])].append(r)

    header = f"{'category':<18}{'difficulty':<10}{'model':<20}{'status':<22}{'latency_ms':>11}{'cost_usd':>12}"
    print(header)
    print("-" * len(header))
    for (category, difficulty, model_id), rows in sorted(by_key.items()):
        for r in rows:
            eval_label = r["evaluation_status"] if r["status"] == "success" else "error"
            latency = f"{r['latency_ms']:.0f}" if r["latency_ms"] is not None else "-"
            cost = f"{r['estimated_cost_usd']:.6f}" if r["estimated_cost_usd"] is not None else "-"
            print(
                f"{category:<18}{difficulty:<10}{model_id:<20}{eval_label:<22}{latency:>11}{cost:>12}"
            )

    # --- aggregate correctness by model, restricted to deterministically-evaluated tasks ---
    print("\ncorrectness on deterministically-evaluated tasks (exact_match / classification_label / valid_json):")
    scored = [r for r in records if r["evaluation_type"] != "manual"]
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in scored:
        by_model[r["model_config_id"]].append(r)
    for model_id, rows in sorted(by_model.items()):
        correct = sum(1 for r in rows if r["evaluation_status"] == "correct")
        errors = sum(1 for r in rows if r["status"] == "error")
        avg_latency = sum(r["latency_ms"] for r in rows if r["latency_ms"]) / max(
            1, sum(1 for r in rows if r["latency_ms"])
        )
        total_cost = sum(r["estimated_cost_usd"] for r in rows if r["estimated_cost_usd"])
        print(
            f"  {model_id:<20} correct={correct}/{len(rows)}  errors={errors}  "
            f"avg_latency_ms={avg_latency:.1f}  total_cost_usd={total_cost:.6f}"
        )


if __name__ == "__main__":
    main()
