"""Evaluation coverage report: for the 104-task Groq real-data benchmark,
how many tasks currently have real ground truth vs. require a human vs.
are a genuine gap.

Three-way split, computed per task (both groq-gpt-oss-20b and
groq-gpt-oss-120b executions considered together):

- automatically graded: evaluation_status is correct/incorrect for BOTH
  models via some deterministic method - the standard evaluate()
  dispatch (exact_match/classification_label/valid_json) OR the
  sandboxed code-execution grader for debugging tasks (which keeps
  evaluation_type="manual" in the task file by design - see
  backend/app/evaluation/sandbox.py's module docstring - so it is
  detected by evaluation_status, not evaluation_type).
- manual-only: evaluation_type == "manual" in the task file AND not
  automatically graded above. A deliberate methodological choice (no
  deterministic grader exists, or one was tried and rejected, e.g.
  debugging-007), not a gap.
- ungraded: evaluation_type is one of the automated types
  (exact_match/classification_label/valid_json) but the task is NOT
  automatically graded above - a genuine coverage gap (e.g. a failed
  execution, or an automated-type task not yet (re)scored).

Every task falls into exactly one bucket. Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/evaluation_coverage_report.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "experiments" / "results" / "groq-gpt-oss-expansion.json"
REPORT_PATH = REPO_ROOT / "experiments" / "results" / "evaluation-coverage-report.md"

MODEL_A = "groq-gpt-oss-20b"
MODEL_B = "groq-gpt-oss-120b"


def main() -> None:
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}
    executions = json.loads(RESULTS_PATH.read_text())["executions"]
    by_task_model = {(e["task_id"], e["model_config_id"]): e for e in executions}
    task_ids = sorted(tasks)

    def is_graded(tid: str) -> bool:
        a = by_task_model.get((tid, MODEL_A))
        b = by_task_model.get((tid, MODEL_B))
        if a is None or b is None:
            return False
        return a["evaluation_status"] in ("correct", "incorrect") and b["evaluation_status"] in (
            "correct",
            "incorrect",
        )

    auto_graded, manual_only, ungraded = [], [], []
    for tid in task_ids:
        if is_graded(tid):
            auto_graded.append(tid)
        elif tasks[tid].evaluation_type.value == "manual":
            manual_only.append(tid)
        else:
            ungraded.append(tid)

    lines: list[str] = []

    def emit(s: str = "") -> None:
        lines.append(s)
        print(s)

    total = len(task_ids)
    emit("# Evaluation coverage report")
    emit()
    emit(f"- total benchmark tasks: {total}")
    emit(f"- automatically graded (real ground truth, both models): {len(auto_graded)}")
    emit(f"- manual-only (evaluation_type=manual, no automated grader applied): {len(manual_only)}")
    emit(f"- ungraded (automated evaluation_type, but not currently scored - a gap): {len(ungraded)}")
    emit(f"- percentage with automated quality labels: {len(auto_graded)/total:.1%}")
    emit()

    emit("## Coverage by category")
    emit()
    emit("| category | total | automatically graded | manual-only | ungraded | automated % |")
    emit("|---|---|---|---|---|---|")
    cats = sorted({t.category.value for t in tasks.values()})
    for cat in cats:
        cat_ids = [tid for tid in task_ids if tasks[tid].category.value == cat]
        n = len(cat_ids)
        n_auto = sum(1 for tid in cat_ids if tid in auto_graded)
        n_manual = sum(1 for tid in cat_ids if tid in manual_only)
        n_ungraded = sum(1 for tid in cat_ids if tid in ungraded)
        emit(f"| {cat} | {n} | {n_auto} | {n_manual} | {n_ungraded} | {n_auto/n:.1%} |")
    emit()

    if ungraded:
        emit("## Ungraded tasks (genuine gap - investigate before trusting coverage numbers)")
        emit()
        gap_by_cat = defaultdict(list)
        for tid in ungraded:
            gap_by_cat[tasks[tid].category.value].append(tid)
        for cat, tids in sorted(gap_by_cat.items()):
            emit(f"- **{cat}**: {sorted(tids)}")
        emit()
    else:
        emit("## Ungraded tasks")
        emit()
        emit("None - every automated-evaluation_type task currently has real ground truth "
             "for both models.")
        emit()

    emit("## Manual-only tasks (deliberate, not a gap)")
    emit()
    manual_by_cat = defaultdict(list)
    for tid in manual_only:
        manual_by_cat[tasks[tid].category.value].append(tid)
    for cat, tids in sorted(manual_by_cat.items()):
        emit(f"- **{cat}**: {sorted(tids)}")
    emit()

    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"\nwrote {REPORT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
