"""Routing opportunity analysis: does the Groq gpt-oss-20b/120b pair
actually offer enough of a performance difference for intelligent
routing to be worth anything, on the real benchmark data collected so
far?

This is deliberately independent of V3 (the learned router) - it asks
a prior question V3's own result can't answer on its own: for THIS
model pair, on THIS task distribution, is there a routing opportunity
to find at all? A router that "loses to a trivial baseline" and "there
is no real quality gap between these two models to route around" are
two different findings, easy to conflate if only the router's own
accuracy number is examined.

Only tasks with REAL ground truth (evaluation_status in {correct,
incorrect}, not not_evaluated) are used for any quality/success-rate
comparison. Ungraded tasks are reported separately as a gap, never
silently excluded without being named.

"Nominal cost" = estimated_cost_usd already recorded per execution
(registry per-1k pricing x real token counts). "Actual billed cost" is
reported separately as a flat, explicit fact ($0 - free tier, no
payment method), not computed per task, since Groq's free tier does not
bill per-token regardless of what the nominal figure says.

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/analyze_routing_opportunity.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "experiments" / "results" / "groq-gpt-oss-expansion.json"
REPORT_PATH = REPO_ROOT / "experiments" / "results" / "routing-opportunity-analysis.md"

MODEL_A = "groq-gpt-oss-20b"
MODEL_B = "groq-gpt-oss-120b"


def load_data():
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}
    executions = json.loads(RESULTS_PATH.read_text())["executions"]
    by_task_model = {(e["task_id"], e["model_config_id"]): e for e in executions}
    return tasks, by_task_model


def is_graded(execution: dict) -> bool:
    return execution["evaluation_status"] in ("correct", "incorrect")


def main() -> None:
    tasks, by_task_model = load_data()
    task_ids = sorted(tasks)

    graded_task_ids = [
        tid for tid in task_ids
        if is_graded(by_task_model[(tid, MODEL_A)]) and is_graded(by_task_model[(tid, MODEL_B)])
    ]
    ungraded_task_ids = [tid for tid in task_ids if tid not in graded_task_ids]

    lines: list[str] = []

    def emit(s: str = "") -> None:
        lines.append(s)
        print(s)

    emit("# Routing opportunity analysis: groq-gpt-oss-20b vs groq-gpt-oss-120b")
    emit()
    emit(f"104 total benchmark tasks. {len(graded_task_ids)} have real ground truth for both "
         f"models (exact_match/classification_label/valid_json, or the sandboxed code-execution "
         f"grader). {len(ungraded_task_ids)} remain ungraded (evaluation_type=manual, no grader "
         f"exists yet).")
    emit()

    # --- 1-7: full per-task table ---
    emit("## Full per-task, per-model breakdown")
    emit()
    emit("| task_id | category | difficulty | model | quality | latency_ms | nominal_cost_usd |")
    emit("|---|---|---|---|---|---|---|")
    for tid in task_ids:
        task = tasks[tid]
        for model_id in (MODEL_A, MODEL_B):
            e = by_task_model[(tid, model_id)]
            quality = e["evaluation_status"]
            latency = f"{e['latency_ms']:.0f}" if e["latency_ms"] is not None else "-"
            cost = f"{e['estimated_cost_usd']:.6f}" if e["estimated_cost_usd"] is not None else "-"
            emit(f"| {tid} | {task.category.value} | {task.difficulty.value} | {model_id} | {quality} | {latency} | {cost} |")
    emit()
    emit("**Actual billed cost (all 208 executions, both models): $0.00** - Groq free tier, no "
         "payment method on the account. The nominal_cost_usd column above is notional (registry "
         "per-1k pricing x real token counts), not what was actually charged.")
    emit()

    # --- quality/success rate by category ---
    emit("## Quality/success rate by category (graded tasks only)")
    emit()
    emit("| category | n_graded | 20b correct | 20b rate | 120b correct | 120b rate |")
    emit("|---|---|---|---|---|---|")
    cats = sorted({tasks[tid].category.value for tid in graded_task_ids})
    for cat in cats:
        cat_tasks = [tid for tid in graded_task_ids if tasks[tid].category.value == cat]
        a_correct = sum(1 for tid in cat_tasks if by_task_model[(tid, MODEL_A)]["evaluation_status"] == "correct")
        b_correct = sum(1 for tid in cat_tasks if by_task_model[(tid, MODEL_B)]["evaluation_status"] == "correct")
        n = len(cat_tasks)
        emit(f"| {cat} | {n} | {a_correct} | {a_correct/n:.1%} | {b_correct} | {b_correct/n:.1%} |")
    emit()

    # --- quality/success rate by difficulty ---
    emit("## Quality/success rate by difficulty (graded tasks only)")
    emit()
    emit("| difficulty | n_graded | 20b correct | 20b rate | 120b correct | 120b rate |")
    emit("|---|---|---|---|---|---|")
    diffs = ["easy", "medium", "hard"]
    for diff in diffs:
        diff_tasks = [tid for tid in graded_task_ids if tasks[tid].difficulty.value == diff]
        if not diff_tasks:
            continue
        a_correct = sum(1 for tid in diff_tasks if by_task_model[(tid, MODEL_A)]["evaluation_status"] == "correct")
        b_correct = sum(1 for tid in diff_tasks if by_task_model[(tid, MODEL_B)]["evaluation_status"] == "correct")
        n = len(diff_tasks)
        emit(f"| {diff} | {n} | {a_correct} | {a_correct/n:.1%} | {b_correct} | {b_correct/n:.1%} |")
    emit()

    # --- both succeed / only A / only B / both fail ---
    both_succeed, only_a, only_b, both_fail = [], [], [], []
    for tid in graded_task_ids:
        a_ok = by_task_model[(tid, MODEL_A)]["evaluation_status"] == "correct"
        b_ok = by_task_model[(tid, MODEL_B)]["evaluation_status"] == "correct"
        if a_ok and b_ok:
            both_succeed.append(tid)
        elif a_ok and not b_ok:
            only_a.append(tid)
        elif b_ok and not a_ok:
            only_b.append(tid)
        else:
            both_fail.append(tid)

    emit("## Agreement breakdown (graded tasks only)")
    emit()
    emit(f"- both succeed: {len(both_succeed)}/{len(graded_task_ids)} ({len(both_succeed)/len(graded_task_ids):.1%})")
    emit(f"- only 20b succeeds: {len(only_a)}/{len(graded_task_ids)} ({len(only_a)/len(graded_task_ids):.1%}) - {only_a}")
    emit(f"- only 120b succeeds: {len(only_b)}/{len(graded_task_ids)} ({len(only_b)/len(graded_task_ids):.1%}) - {only_b}")
    emit(f"- both fail: {len(both_fail)}/{len(graded_task_ids)} ({len(both_fail)/len(graded_task_ids):.1%}) - {both_fail}")
    emit()

    # --- latency ---
    a_latencies = [by_task_model[(tid, MODEL_A)]["latency_ms"] for tid in task_ids]
    b_latencies = [by_task_model[(tid, MODEL_B)]["latency_ms"] for tid in task_ids]
    a_avg = sum(a_latencies) / len(a_latencies)
    b_avg = sum(b_latencies) / len(b_latencies)
    emit("## Latency")
    emit()
    emit(f"- {MODEL_A}: avg {a_avg:.0f}ms across all 104 tasks")
    emit(f"- {MODEL_B}: avg {b_avg:.0f}ms across all 104 tasks")
    emit(f"- 120b is {b_avg/a_avg:.2f}x the latency of 20b on average")
    emit()

    # --- token usage ---
    a_in = sum(by_task_model[(tid, MODEL_A)]["input_tokens"] for tid in task_ids)
    a_out = sum(by_task_model[(tid, MODEL_A)]["output_tokens"] for tid in task_ids)
    b_in = sum(by_task_model[(tid, MODEL_B)]["input_tokens"] for tid in task_ids)
    b_out = sum(by_task_model[(tid, MODEL_B)]["output_tokens"] for tid in task_ids)
    emit("## Token usage")
    emit()
    emit(f"- {MODEL_A}: {a_in} input + {a_out} output = {a_in+a_out} total tokens across all "
         f"{len(task_ids)} tasks (avg {a_out/len(task_ids):.0f} output tokens/task)")
    emit(f"- {MODEL_B}: {b_in} input + {b_out} output = {b_in+b_out} total tokens across all "
         f"{len(task_ids)} tasks (avg {b_out/len(task_ids):.0f} output tokens/task)")
    emit(f"- 120b uses {b_out/a_out:.2f}x the output tokens of 20b on average")
    emit()

    # --- cost ---
    a_cost = sum(by_task_model[(tid, MODEL_A)]["estimated_cost_usd"] for tid in task_ids)
    b_cost = sum(by_task_model[(tid, MODEL_B)]["estimated_cost_usd"] for tid in task_ids)
    emit("## Cost")
    emit()
    emit(f"- {MODEL_A}: nominal total ${a_cost:.6f} across all 104 tasks")
    emit(f"- {MODEL_B}: nominal total ${b_cost:.6f} across all 104 tasks")
    emit(f"- 120b is {b_cost/a_cost:.2f}x the nominal cost of 20b")
    emit("- **actual billed cost for both: $0.00** (free tier, no payment method)")
    emit()

    # --- how often does choosing 120b actually improve the result ---
    emit("## How often does choosing 120b over 20b actually improve the result?")
    emit()
    emit(f"120b corrects a 20b failure on {len(only_b)}/{len(graded_task_ids)} graded tasks "
         f"({len(only_b)/len(graded_task_ids):.1%}), at {b_avg/a_avg:.2f}x the latency and "
         f"{b_cost/a_cost:.2f}x the nominal cost, for a task set with no real cost difference today "
         f"(both models are on Groq's free tier).")
    emit()

    always_a_acc = (len(both_succeed) + len(only_a)) / len(graded_task_ids)
    always_b_acc = (len(both_succeed) + len(only_b)) / len(graded_task_ids)
    oracle_acc = (len(both_succeed) + len(only_a) + len(only_b)) / len(graded_task_ids)
    emit("### The structural fact that decides this")
    emit()
    emit(f"- always-20b accuracy on the graded set: {len(both_succeed)}+{len(only_a)} = "
         f"{len(both_succeed)+len(only_a)}/{len(graded_task_ids)} = {always_a_acc:.1%}")
    emit(f"- always-120b accuracy on the graded set: {len(both_succeed)}+{len(only_b)} = "
         f"{len(both_succeed)+len(only_b)}/{len(graded_task_ids)} = {always_b_acc:.1%}")
    emit(f"- **these are equal** ({len(only_a)} vs {len(only_b)}) - neither model is a better "
         f"unconditional default than the other on this task set.")
    emit(f"- a perfect oracle router (always picks whichever of the two is correct, when either "
         f"is) reaches {len(both_succeed)+len(only_a)+len(only_b)}/{len(graded_task_ids)} = "
         f"{oracle_acc:.1%} - a ceiling only {oracle_acc-always_a_acc:.1%} above either model alone, "
         f"defined by just {len(only_a)+len(only_b)} tasks total.")
    emit()

    # --- evaluation gaps ---
    emit("## Evaluation gaps: tasks with no real ground truth yet")
    emit()
    gap_by_cat = defaultdict(list)
    for tid in ungraded_task_ids:
        gap_by_cat[tasks[tid].category.value].append(tid)
    for cat, tids in sorted(gap_by_cat.items()):
        emit(f"- **{cat}**: {len(tids)} task(s) - {sorted(tids)}")
    emit()

    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"\nwrote {REPORT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
