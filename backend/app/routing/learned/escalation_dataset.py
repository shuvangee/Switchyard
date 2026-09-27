"""V3 escalation-target training dataset: built ONLY from real
groq-gpt-oss-20b/120b evaluation results (experiments/results/groq-gpt-
oss-expansion.json), restricted to the 92 tasks with real ground truth
for both models — the same set analyze_simple_routing_baselines.py and
analyze_routing_opportunity.py use. The 12 manual-only tasks are
excluded: no trustworthy label exists for them, and CLAUDE.md forbids
inventing one.

TRAINING TARGET, and why this shape: not "predict the stronger model"
(that's what dataset.py's older cheapest-correct-candidate target does,
across a different, mixed mock/gemini/groq dataset — left untouched,
still backing the original learned-v1 artifact). This target directly
encodes Switchyard's actual operating goal: use the cheap model (20b)
unless the expensive one (120b) provides enough real, observed quality
benefit to justify escalating. So the label is binary — "escalate" —
defined from the REAL recorded evaluation_status of both models on each
task:

- only 120b correct (20b wrong)  -> escalate = True  (120b earns its cost)
- both correct                   -> escalate = False (20b already enough)
- only 20b correct                -> escalate = False (120b would be WRONG)
- both incorrect                  -> escalate = False (escalating buys
  nothing here — quality is unaffected either way, so the cost-
  minimizing choice is the correct one to train toward)

Documented in docs/case-study/DECISIONS.md (2026-09-27 V3 entry). Every
one of the 92 graded tasks gets a row and a defined label — none of the
four outcome cases is silently dropped.

Features come from the SAME heuristic analyzer used at inference time
(analyze_request) and the SAME encode() used by the original learned-v1
pipeline (app.routing.learned.features) — category, difficulty,
structured_output_required, estimated_input_tokens. No model response,
evaluation result, latency, or output-token count is ever a feature:
those only exist after a model has already run and would leak the
target (they're stored on EscalationRow purely so LOOCV evaluation can
score a held-out prediction against the REAL recorded outcome for
whichever model the classifier picks — never fed back in as an input).
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks
from app.routing.analyzer import RequestAnalysis, analyze_request

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RESULTS_PATH = REPO_ROOT / "experiments" / "results" / "groq-gpt-oss-expansion.json"

MODEL_20B_ID = "groq-gpt-oss-20b"
MODEL_120B_ID = "groq-gpt-oss-120b"


@dataclass(frozen=True)
class EscalationRow:
    task_id: str
    analysis: RequestAnalysis
    escalate: bool  # the training label

    # Real, already-recorded outcomes for BOTH models on this task —
    # used only for scoring a held-out prediction (LOOCV), never as a
    # training feature.
    correct_20b: bool
    correct_120b: bool
    latency_20b_ms: float
    latency_120b_ms: float
    cost_20b_usd: float
    cost_120b_usd: float


def _is_graded(execution: dict) -> bool:
    return execution["evaluation_status"] in ("correct", "incorrect")


def build_escalation_rows(
    results_path: Path | None = None,
    benchmarks_dir: Path | None = None,
) -> tuple[list[EscalationRow], dict[str, int]]:
    """Returns (rows, excluded_counts). excluded_counts always sums with
    len(rows) to the total benchmark task count, and is reported in the
    training manifest so the dataset's real size is never presented
    without also showing what was left out and why.
    """
    results_path = results_path or DEFAULT_RESULTS_PATH
    tasks = {t.id: t for t in load_benchmark_tasks(benchmarks_dir or default_benchmarks_dir())}
    executions = json.loads(results_path.read_text())["executions"]
    by_task_model = {(e["task_id"], e["model_config_id"]): e for e in executions}

    rows: list[EscalationRow] = []
    excluded = {"no_ground_truth_for_both_models": 0}

    for task_id, task in tasks.items():
        exec_20b = by_task_model.get((task_id, MODEL_20B_ID))
        exec_120b = by_task_model.get((task_id, MODEL_120B_ID))
        if exec_20b is None or exec_120b is None or not (_is_graded(exec_20b) and _is_graded(exec_120b)):
            excluded["no_ground_truth_for_both_models"] += 1
            continue

        correct_20b = exec_20b["evaluation_status"] == "correct"
        correct_120b = exec_120b["evaluation_status"] == "correct"
        escalate = correct_120b and not correct_20b  # only-120b-correct is the sole escalate=True case

        rows.append(
            EscalationRow(
                task_id=task_id,
                analysis=analyze_request(task.prompt),
                escalate=escalate,
                correct_20b=correct_20b,
                correct_120b=correct_120b,
                latency_20b_ms=exec_20b["latency_ms"],
                latency_120b_ms=exec_120b["latency_ms"],
                cost_20b_usd=exec_20b["estimated_cost_usd"],
                cost_120b_usd=exec_120b["estimated_cost_usd"],
            )
        )

    return rows, excluded
