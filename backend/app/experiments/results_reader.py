"""Reads the committed, real offline benchmark results directly from
disk — the same pattern already used by `routing/learned/train_
escalation.py`'s manifest and `api/analytics.py`'s router-comparison
endpoint.

WHY this exists: a fresh deployment's database has NO benchmark
execution rows in it. The real 92-task Groq run
(experiments/results/groq-gpt-oss-expansion.json) was produced by
standalone scripts writing directly into whichever developer's local
`backend/switchyard.db` happened to run them, then serialized to this
committed JSON file — `model_executions` on a fresh clone is empty (see
docs/case-study/DECISIONS.md, 2026-09-28, for the full trace). Rather
than build a database-rehydration importer (a bigger, riskier change
for V4's scope), the product reads the same real, git-tracked artifact
every case-study document already cites — same data, same numbers,
just queryable through the API instead of only living in markdown.

Every function here is a pure read of committed data. Nothing is
computed from live request traffic, and nothing is fabricated —an
empty/missing file returns an empty result, never an invented one.
"""

import json
from pathlib import Path
from typing import Any

from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_PATH = REPO_ROOT / "experiments" / "results" / "groq-gpt-oss-expansion.json"

GRADED_STATUSES = ("correct", "incorrect")


def _load_executions() -> list[dict]:
    if not RESULTS_PATH.exists():
        return []
    return json.loads(RESULTS_PATH.read_text())["executions"]


def _is_graded(execution: dict) -> bool:
    return execution["evaluation_status"] in GRADED_STATUSES


def model_benchmark_performance(model_config_id: str) -> dict[str, Any] | None:
    """Real, measured performance for one model on the committed 92-task
    benchmark — accuracy/latency/cost from actual recorded executions,
    never estimated. Returns None if this model has no executions in the
    committed results (e.g. any non-Groq model_config_id).
    """
    executions = [e for e in _load_executions() if e["model_config_id"] == model_config_id]
    if not executions:
        return None

    # Latency/cost restricted to the 92 graded executions, matching the
    # headline numbers already published throughout the case study
    # (scripts/analyze_simple_routing_baselines.py's methodology) - the
    # 12 ungraded tasks' executions exist (all 104 were called) but
    # aren't part of the number anyone else quotes.
    graded = [e for e in executions if _is_graded(e)]
    correct = sum(1 for e in graded if e["evaluation_status"] == "correct")
    latencies = [e["latency_ms"] for e in graded if e.get("latency_ms") is not None]
    costs = [e["estimated_cost_usd"] for e in graded if e.get("estimated_cost_usd") is not None]

    return {
        "n_executions": len(executions),
        "n_graded": len(graded),
        "n_correct": correct,
        "accuracy": (correct / len(graded)) if graded else None,
        "avg_latency_ms": (sum(latencies) / len(latencies)) if latencies else None,
        "nominal_cost_usd": sum(costs) if costs else None,
    }


def evaluation_coverage(benchmarks_dir: Path | None = None) -> dict[str, Any]:
    """Real evaluation-coverage breakdown, mirroring
    scripts/evaluation_coverage_report.py's logic exactly: a task counts
    as automatically graded if BOTH groq-gpt-oss-20b and -120b have a
    real evaluation_status for it, regardless of the task's own
    evaluation_type field (the sandbox/required-facts graders are
    deliberately not wired into EvaluationType — see
    backend/app/evaluation/sandbox.py).
    """
    tasks = {t.id: t for t in load_benchmark_tasks(benchmarks_dir or default_benchmarks_dir())}
    executions = _load_executions()
    by_task_model = {(e["task_id"], e["model_config_id"]): e for e in executions}
    model_ids = ("groq-gpt-oss-20b", "groq-gpt-oss-120b")

    def is_task_graded(task_id: str) -> bool:
        for model_id in model_ids:
            execution = by_task_model.get((task_id, model_id))
            if execution is None or not _is_graded(execution):
                return False
        return True

    total = len(tasks)
    auto_graded_ids = [tid for tid in tasks if is_task_graded(tid)]
    auto_graded = len(auto_graded_ids)

    by_category: dict[str, dict[str, int]] = {}
    for tid, task in tasks.items():
        cat = task.category.value
        by_category.setdefault(cat, {"total": 0, "auto_graded": 0, "manual_only": 0, "ungraded": 0})
        by_category[cat]["total"] += 1
        if tid in auto_graded_ids:
            by_category[cat]["auto_graded"] += 1
        elif task.evaluation_type.value == "manual":
            by_category[cat]["manual_only"] += 1
        else:
            by_category[cat]["ungraded"] += 1

    manual_only = sum(
        1 for tid, task in tasks.items() if tid not in auto_graded_ids and task.evaluation_type.value == "manual"
    )
    ungraded = total - auto_graded - manual_only

    return {
        "total_tasks": total,
        "auto_graded": auto_graded,
        "manual_only": manual_only,
        "ungraded": ungraded,
        "automated_pct": (auto_graded / total) if total else None,
        "by_category": by_category,
    }
