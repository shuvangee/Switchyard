"""V3 training dataset construction.

Builds one training row per benchmark task, from the experiment result
files that actually exist in this repo: the V0 mock baseline
(experiments/results/v0-mock-baseline.json), the first real-provider
experiment (experiments/results/gemini-3.6-flash-baseline.json), and the
Groq gpt-oss-20b/120b run against the expanded 104-task set
(experiments/results/groq-gpt-oss-expansion.json, added 2026-09-23 —
run from outside this sandbox, since this environment's network policy
blocks groq.com; see FAILURES_AND_LESSONS.md).

TRAINING TARGET, and why: for each task, the target is the *cheapest*
candidate model that got the task CORRECT. This directly encodes
Switchyard's research question (can a router pick a cheaper model without
losing correctness) as a supervised label. It only exists for tasks with
a deterministic evaluator (exact_match / classification_label /
valid_json) — the 4 manual-eval categories have no ground truth to check
"correct" against, so they contribute no training rows. A task where NO
candidate model got it right also contributes no row: there is no valid
"correct and cheap" choice to learn from, and inventing one would be
fabricating a label.

Features are computed via the SAME heuristic analyzer used at inference
time (analyze_request), not the benchmark task's authored ground-truth
category/difficulty. Training on the authored labels would create
train/serve skew: the real router never sees ground truth at inference
time, only the analyzer's guess. See docs/case-study/DECISIONS.md.

KNOWN LIMITATION, stated here because it shapes every downstream result:
rows only exist for tasks with a deterministic evaluator (see TRAINING
TARGET above), and among those, a row's candidate set only ever includes
whichever models actually have a recorded execution for that specific
task — the three mock models (all 104 tasks), gemini-3.6-flash (only the
original 12), and the two Groq models (only the 104 auto-gradeable-type
tasks that exist as of the 2026-09-22 expansion, which happens to be all
of them for math/classification/extraction/structured_output plus the 5
exact_match reasoning tasks). This dataset does not resolve the
MockProvider-heuristic leakage risk raised in the 2026-09-19 V3
data-readiness review for tasks where mock candidates dominate the
correct-and-cheap comparison; it is the smallest real, non-fabricated
dataset that exists today.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks
from app.models.enums import TaskCategory, TaskDifficulty
from app.routing.analyzer import RequestAnalysis, analyze_request

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RESULT_FILES = [
    REPO_ROOT / "experiments/results/v0-mock-baseline.json",
    REPO_ROOT / "experiments/results/gemini-3.6-flash-baseline.json",
    REPO_ROOT / "experiments/results/groq-gpt-oss-expansion.json",
]


@dataclass(frozen=True)
class Candidate:
    model_config_id: str
    correct: bool
    estimated_cost_usd: float | None


@dataclass(frozen=True)
class TrainingRow:
    task_id: str
    analysis: RequestAnalysis
    candidates: tuple[Candidate, ...]
    target_model_id: str  # cheapest candidate with correct == True


def _load_executions(result_files: list[Path]) -> dict[str, list[dict]]:
    """task_id -> list of raw execution dicts, across all given result files."""
    by_task: dict[str, list[dict]] = {}
    for path in result_files:
        data = json.loads(path.read_text())
        for execution in data["executions"]:
            by_task.setdefault(execution["task_id"], []).append(execution)
    return by_task


def build_training_rows(
    result_files: list[Path] | None = None,
    benchmarks_dir: Path | None = None,
) -> tuple[list[TrainingRow], dict[str, int]]:
    """Returns (rows, exclusion_counts). exclusion_counts explains, per
    reason, how many benchmark tasks did NOT produce a training row —
    reported in the case study so the dataset size is never presented
    without also showing what was dropped and why.

    benchmarks_dir defaults to the real benchmarks/tasks/ directory; tests
    pass an isolated directory of synthetic tasks instead.
    """
    result_files = result_files or DEFAULT_RESULT_FILES
    tasks = {t.id: t for t in load_benchmark_tasks(benchmarks_dir or default_benchmarks_dir())}
    executions_by_task = _load_executions(result_files)

    rows: list[TrainingRow] = []
    excluded = {"manual_eval_type": 0, "no_correct_candidate": 0, "no_executions": 0}

    for task_id, task in tasks.items():
        if task.evaluation_type.value == "manual":
            excluded["manual_eval_type"] += 1
            continue

        executions = executions_by_task.get(task_id, [])
        if not executions:
            excluded["no_executions"] += 1
            continue

        candidates = tuple(
            Candidate(
                model_config_id=e["model_config_id"],
                correct=(e["status"] == "success" and e["evaluation_status"] == "correct"),
                estimated_cost_usd=e.get("estimated_cost_usd"),
            )
            for e in executions
        )
        correct_candidates = [c for c in candidates if c.correct and c.estimated_cost_usd is not None]
        if not correct_candidates:
            excluded["no_correct_candidate"] += 1
            continue

        target = min(correct_candidates, key=lambda c: c.estimated_cost_usd)
        analysis = analyze_request(task.prompt)
        rows.append(
            TrainingRow(
                task_id=task_id,
                analysis=analysis,
                candidates=candidates,
                target_model_id=target.model_config_id,
            )
        )

    return rows, excluded


def category_options() -> list[str]:
    return [c.value for c in TaskCategory]


def difficulty_options() -> list[str]:
    return [d.value for d in TaskDifficulty]
