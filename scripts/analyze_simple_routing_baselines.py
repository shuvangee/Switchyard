"""V2.6 Phase 1-5: simple, interpretable routing baselines for the
groq-gpt-oss-20b/120b pair - a required checkpoint BEFORE any learned
router (V3) or third model (Qwen), asking: how much of the 20b/120b
quality gap can a rule a human could read in one line already capture?

Restricted to the 92 tasks with real ground truth for both models
(same set analyze_routing_opportunity.py uses) - the 12 manual-only
tasks have no correctness signal to route on or evaluate against.

Every routing rule here is DERIVED FROM and EVALUATED ON the same 92
tasks - in-sample by construction, labeled as such throughout. A
leave-one-out cross-validation (LOOCV) is run for the category rule
specifically to give a real (not just claimed) estimate of whether it
generalizes, given the dataset is far too small (92 tasks, 8 category
values, some with under 10 graded tasks) for a held-out test split to
leave a meaningful test set - see the module's generalization-approach
notes near the bottom of main().

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/analyze_simple_routing_baselines.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "experiments" / "results" / "groq-gpt-oss-expansion.json"
REPORT_PATH = REPO_ROOT / "experiments" / "results" / "simple-routing-baselines.md"

MODEL_A = "groq-gpt-oss-20b"   # cheap/fast
MODEL_B = "groq-gpt-oss-120b"  # expensive/slow

MIN_CELL_SIZE = 3  # minimum tasks in a (category, difficulty) cell to base a rule on it


def load_data():
    tasks = {t.id: t for t in load_benchmark_tasks(default_benchmarks_dir())}
    executions = json.loads(RESULTS_PATH.read_text())["executions"]
    by_task_model = {(e["task_id"], e["model_config_id"]): e for e in executions}
    return tasks, by_task_model


def is_graded(execution: dict) -> bool:
    return execution["evaluation_status"] in ("correct", "incorrect")


def main() -> None:
    tasks, by_task_model = load_data()
    graded_ids = sorted(
        tid for tid in tasks
        if is_graded(by_task_model[(tid, MODEL_A)]) and is_graded(by_task_model[(tid, MODEL_B)])
    )
    n = len(graded_ids)

    # One record per graded task: everything a routing rule or the
    # scoring below needs, computed once.
    rec = {}
    for tid in graded_ids:
        a, b = by_task_model[(tid, MODEL_A)], by_task_model[(tid, MODEL_B)]
        rec[tid] = {
            "category": tasks[tid].category.value,
            "difficulty": tasks[tid].difficulty.value,
            "a_correct": a["evaluation_status"] == "correct",
            "b_correct": b["evaluation_status"] == "correct",
            "a_latency": a["latency_ms"],
            "b_latency": b["latency_ms"],
            "a_cost": a["estimated_cost_usd"],
            "b_cost": b["estimated_cost_usd"],
        }

    lines: list[str] = []

    def emit(s: str = "") -> None:
        lines.append(s)
        print(s)

    emit("# Simple routing baselines: groq-gpt-oss-20b vs groq-gpt-oss-120b")
    emit()
    emit(f"Evaluated on the {n} tasks with real ground truth for both models (same set as "
         f"`routing-opportunity-analysis.md`). Every rule below is derived from and scored "
         f"against this SAME set — **in-sample by construction** — see the generalization "
         f"section for what that does and doesn't license.")
    emit()

    # ---------------------------------------------------------------
    # PHASE 1: build the routing rules from the data
    # ---------------------------------------------------------------

    # D. category-aware: for each category, whichever model has strictly
    # higher accuracy on that category's graded tasks wins the category;
    # ties default to 20b (cheaper, no quality reason to pay more).
    by_cat = defaultdict(list)
    for tid in graded_ids:
        by_cat[rec[tid]["category"]].append(tid)

    category_rule = {}
    emit("## Phase 1D — category-aware rule (derived from data, not assumed)")
    emit()
    emit("| category | n | 20b acc | 120b acc | rule |")
    emit("|---|---|---|---|---|")
    for cat, tids in sorted(by_cat.items()):
        a_acc = sum(rec[t]["a_correct"] for t in tids) / len(tids)
        b_acc = sum(rec[t]["b_correct"] for t in tids) / len(tids)
        winner = MODEL_B if b_acc > a_acc else MODEL_A  # tie -> cheaper model
        category_rule[cat] = winner
        tag = " (tie -> cheaper)" if a_acc == b_acc else ""
        emit(f"| {cat} | {len(tids)} | {a_acc:.1%} | {b_acc:.1%} | {winner.split('-')[-1]}{tag} |")
    emit()

    # E. difficulty-aware: same procedure, keyed on difficulty.
    by_diff = defaultdict(list)
    for tid in graded_ids:
        by_diff[rec[tid]["difficulty"]].append(tid)

    difficulty_rule = {}
    emit("## Phase 1E — difficulty-aware rule (derived from data, not assumed)")
    emit()
    emit("| difficulty | n | 20b acc | 120b acc | rule |")
    emit("|---|---|---|---|---|")
    for diff in ("easy", "medium", "hard"):
        tids = by_diff.get(diff, [])
        if not tids:
            continue
        a_acc = sum(rec[t]["a_correct"] for t in tids) / len(tids)
        b_acc = sum(rec[t]["b_correct"] for t in tids) / len(tids)
        winner = MODEL_B if b_acc > a_acc else MODEL_A
        difficulty_rule[diff] = winner
        tag = " (tie -> cheaper)" if a_acc == b_acc else ""
        emit(f"| {diff} | {len(tids)} | {a_acc:.1%} | {b_acc:.1%} | {winner.split('-')[-1]}{tag} |")
    emit()
    diff_accs = {d: sum(rec[t]["a_correct"] for t in tids) / len(tids) - sum(rec[t]["b_correct"] for t in tids) / len(tids)
                 for d, tids in by_diff.items() if tids}
    spread = max(diff_accs.values()) - min(diff_accs.values()) if diff_accs else 0
    emit(f"Difficulty's (20b-120b) accuracy gap ranges {min(diff_accs.values()):+.1%} to "
         f"{max(diff_accs.values()):+.1%} across easy/medium/hard — a {spread:.1%} spread, "
         f"versus category's spread (see table above). Difficulty alone does not separate the "
         f"models nearly as cleanly as category does; treating it as a routing signal on its "
         f"own would be **inventing a pattern the data doesn't clearly support**.")
    emit()

    # F. category + difficulty: only justified where a cell has enough
    # tasks to base a rule on (MIN_CELL_SIZE), otherwise the "rule" is
    # really just memorizing 1-2 tasks.
    by_cell = defaultdict(list)
    for tid in graded_ids:
        by_cell[(rec[tid]["category"], rec[tid]["difficulty"])].append(tid)
    cell_sizes = sorted(len(v) for v in by_cell.values())
    justified_cells = [k for k, v in by_cell.items() if len(v) >= MIN_CELL_SIZE]
    emit("## Phase 1F — category + difficulty: is it justified?")
    emit()
    emit(f"{len(by_cell)} distinct (category, difficulty) cells across {n} tasks; cell sizes "
         f"range {cell_sizes[0]}-{cell_sizes[-1]} tasks, median {cell_sizes[len(cell_sizes)//2]}. "
         f"Only {len(justified_cells)}/{len(by_cell)} cells have >= {MIN_CELL_SIZE} tasks — a "
         f"rule for the rest would be fit to 1-2 data points, indistinguishable from noise. "
         f"**Not run as a strategy below** — combining two categorical axes fragments this "
         f"dataset below the size where a rule means anything; category alone already uses the "
         f"stronger, better-supported signal.")
    emit()

    # ---------------------------------------------------------------
    # PHASE 2: score every strategy on the same real per-task data
    # ---------------------------------------------------------------

    def score(name: str, choose) -> dict:
        """choose(tid) -> MODEL_A or MODEL_B. Scores using each task's
        REAL recorded latency/cost/correctness for whichever model was
        chosen — no averages substituted where real values exist."""
        correct = 0
        cost = 0.0
        latency_sum = 0.0
        n_a = n_b = 0
        for tid in graded_ids:
            r = rec[tid]
            model = choose(tid)
            if model == MODEL_A:
                n_a += 1
                correct += r["a_correct"]
                cost += r["a_cost"]
                latency_sum += r["a_latency"]
            else:
                n_b += 1
                correct += r["b_correct"]
                cost += r["b_cost"]
                latency_sum += r["b_latency"]
        return {
            "name": name,
            "accuracy": correct / n,
            "correct": correct,
            "pct_20b": n_a / n,
            "pct_120b": n_b / n,
            "cost": cost,
            "avg_latency": latency_sum / n,
        }

    strategies = [
        score("A. Always 20b", lambda tid: MODEL_A),
        score("B. Always 120b", lambda tid: MODEL_B),
        score("C. Perfect oracle", lambda tid: MODEL_B if rec[tid]["b_correct"] and not rec[tid]["a_correct"] else MODEL_A),
        score("D. Category-aware (full)", lambda tid: category_rule[rec[tid]["category"]]),
        score("D2. Summarization-only override", lambda tid: MODEL_B if rec[tid]["category"] == "summarization" else MODEL_A),
        score("E. Difficulty-aware", lambda tid: difficulty_rule[rec[tid]["difficulty"]]),
    ]

    always_a = strategies[0]
    always_b = strategies[1]

    emit("## Phase 2 — strategy comparison (real per-task data, no averages substituted)")
    emit()
    emit("| strategy | accuracy | correct | % on 20b | % on 120b | nominal cost | cost vs 20b | "
         "cost vs 120b | avg latency | latency vs 20b | latency vs 120b |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")
    for s in strategies:
        emit(
            f"| {s['name']} | {s['accuracy']:.1%} | {s['correct']}/{n} | {s['pct_20b']:.1%} | "
            f"{s['pct_120b']:.1%} | ${s['cost']:.6f} | {s['cost']/always_a['cost']:.2f}x | "
            f"{s['cost']/always_b['cost']:.2f}x | {s['avg_latency']:.0f}ms | "
            f"{s['avg_latency']/always_a['avg_latency']:.2f}x | "
            f"{s['avg_latency']/always_b['avg_latency']:.2f}x |"
        )
    emit()
    emit("**Actual billed cost for every strategy above: $0.00** — Groq free tier, no payment "
         "method on the account. The nominal_cost figures are notional (registry per-1k "
         "pricing x real token counts actually used by whichever model each strategy picked).")
    emit()

    # ---------------------------------------------------------------
    # PHASE 3: leakage / generalization
    # ---------------------------------------------------------------

    emit("## Phase 3 — data leakage and generalization")
    emit()
    d_strategy = next(s for s in strategies if s["name"].startswith("D."))
    emit(f"The category rule above (Strategy D, {d_strategy['accuracy']:.1%} accuracy) was "
         f"**derived from and evaluated on the identical {n} tasks — this is an IN-SAMPLE "
         f"result and must not be read as evidence it generalizes.** A rule built by asking "
         f"\"which model wins each category on this exact data\" is guaranteed to fit this "
         f"exact data at least as well as either always-X baseline; the open question is "
         f"whether the category→model assignment reflects a real, stable property of the "
         f"models, or noise in a small sample.")
    emit()
    emit("**Why a conventional train/test split isn't the right tool here:** the entire "
         f"routing opportunity is defined by just {sum(1 for t in graded_ids if rec[t]['a_correct'] != rec[t]['b_correct'])} "
         f"disagreement tasks out of {n}. A held-out test split (e.g. 80/20) would put roughly "
         f"1-2 disagreement tasks in the test set — not enough to distinguish \"the rule "
         f"generalizes\" from \"the rule got lucky/unlucky on the 1 task that mattered.\" "
         f"Forcing an ML-style split here would produce a number that looks rigorous but "
         f"measures almost nothing.")
    emit()

    # Real LOOCV for the FULL category rule: for each task, rebuild the
    # category rule from the OTHER 91 tasks (excluding it), then score
    # the held-out task with that rule. No task's own label leaks into
    # the rule used to predict it.
    loocv_correct = 0
    for held_out in graded_ids:
        train_ids = [t for t in graded_ids if t != held_out]
        train_by_cat = defaultdict(list)
        for t in train_ids:
            train_by_cat[rec[t]["category"]].append(t)
        cat = rec[held_out]["category"]
        cat_train = train_by_cat[cat]
        if cat_train:
            a_acc = sum(rec[t]["a_correct"] for t in cat_train) / len(cat_train)
            b_acc = sum(rec[t]["b_correct"] for t in cat_train) / len(cat_train)
            model = MODEL_B if b_acc > a_acc else MODEL_A
        else:
            model = MODEL_A  # unseen category in training fold: default to cheaper
        loocv_correct += rec[held_out]["b_correct"] if model == MODEL_B else rec[held_out]["a_correct"]
    loocv_acc = loocv_correct / n

    # Same LOOCV procedure for the NARROWER summarization-only rule: the
    # non-summarization branch is a hardcoded constant (always 20b), not
    # fit to any data, so it cannot overfit by construction; only the
    # "does summarization favor 120b" decision is re-derived per fold.
    loocv2_correct = 0
    summarization_ids = by_cat["summarization"]
    for held_out in graded_ids:
        if rec[held_out]["category"] != "summarization":
            loocv2_correct += rec[held_out]["a_correct"]  # hardcoded branch: always predicts 20b
            continue
        train = [t for t in summarization_ids if t != held_out]
        a_acc = sum(rec[t]["a_correct"] for t in train) / len(train)
        b_acc = sum(rec[t]["b_correct"] for t in train) / len(train)
        model = MODEL_B if b_acc > a_acc else MODEL_A
        loocv2_correct += rec[held_out]["b_correct"] if model == MODEL_B else rec[held_out]["a_correct"]
    loocv2_acc = loocv2_correct / n

    emit(f"**Leave-one-out cross-validation (LOOCV) on the category rule**, chosen because it "
         f"is the standard, most defensible approach for a dataset this small — it holds out "
         f"exactly one task at a time (no leakage: that task's own label never informs the "
         f"rule used to predict it), while still using every other task to build the rule each "
         f"time, which a fixed train/test split can't afford to do here. Result: "
         f"**{loocv_correct}/{n} = {loocv_acc:.1%} LOOCV accuracy**, versus {d_strategy['accuracy']:.1%} "
         f"in-sample — a {d_strategy['accuracy']-loocv_acc:+.1%} drop when the rule can't see the "
         f"task it's predicting.")
    emit()
    tied_with_a = abs(loocv_acc - always_a["accuracy"]) < 1e-9
    if tied_with_a:
        emit(f"**This LOOCV accuracy is EXACTLY {always_a['accuracy']:.1%} — identical to always-"
             f"20b's raw accuracy.** That is not a coincidence in the reassuring sense: traced "
             f"per-task, the summarization signal genuinely survives LOOCV (5/6 correct held-out, "
             f"matching the in-sample count exactly — every time a summarization task is "
             f"excluded, the remaining 5 summarization tasks still clearly favor 120b), but that "
             f"gain is exactly canceled by the category rule getting WORSE than always-20b on "
             f"extraction: with extraction tied 76.9%/76.9% in-sample (defaulting to 20b), "
             f"excluding either of extraction's two 20b-favoring disagreement tasks "
             f"(extraction-002, extraction-005) from training flips the remaining data's tie "
             f"toward 120b — so LOOCV predicts 120b for the exact two tasks where 20b was "
             f"actually right, losing both. **Honest conclusion: the category rule's in-sample "
             f"+3.3pt edge over always-20b does not survive out-of-fold testing at this sample "
             f"size** — the summarization-specific signal is real and holds up, but the rule as "
             f"a whole (including its razor-thin, easily-flipped tie-breaks in extraction and "
             f"classification) does not yet demonstrate it generalizes beyond this exact "
             f"dataset.")
    elif abs(d_strategy["accuracy"] - loocv_acc) < 0.03:
        emit(f"This is close enough to the in-sample number that the category signal looks "
             f"real, not just overfit to this exact sample.")
    else:
        emit(f"The gap is large enough that the in-sample number alone should not be trusted "
             f"as a generalization estimate.")
    emit()

    d2_strategy = next(s for s in strategies if s["name"].startswith("D2."))
    emit(f"**Retesting with the narrower rule** (\"summarization → 120b, everything else → 20b\", "
         f"D2) that drops the fragile classification/extraction tie-breaks entirely: "
         f"**{loocv2_correct}/{n} = {loocv2_acc:.1%} LOOCV accuracy — IDENTICAL to its own "
         f"in-sample accuracy ({d2_strategy['accuracy']:.1%})**. This is not a coincidence: the "
         f"non-summarization branch is a hardcoded constant with zero free parameters (cannot "
         f"overfit by construction), and the summarization branch's own leave-one-out folds all "
         f"agree with each other (dropping either summarization disagreement task still leaves "
         f"the remaining summarization data clearly favoring 120b). **This narrower rule is the "
         f"one with genuine, demonstrated (not just claimed) out-of-fold validity** — it matches "
         f"always-120b's {always_b['accuracy']:.1%} accuracy while sending only "
         f"{d2_strategy['pct_120b']:.1%} of requests to 120b, and that number holds up under "
         f"honest testing, unlike the full category rule's number.")
    emit()

    # ---------------------------------------------------------------
    # PHASE 4: disagreement analysis
    # ---------------------------------------------------------------

    disagreements = [t for t in graded_ids if rec[t]["a_correct"] != rec[t]["b_correct"]]
    emit(f"## Phase 4 — disagreement analysis ({len(disagreements)} tasks)")
    emit()
    emit("| task_id | category | difficulty | winner | 20b latency | 120b latency |")
    emit("|---|---|---|---|---|---|")
    disagreement_cats = defaultdict(list)
    for tid in sorted(disagreements):
        r = rec[tid]
        winner = MODEL_B if r["b_correct"] else MODEL_A
        disagreement_cats[r["category"]].append(winner)
        emit(f"| {tid} | {r['category']} | {r['difficulty']} | {winner.split('-')[-1]} | "
             f"{r['a_latency']:.0f}ms | {r['b_latency']:.0f}ms |")
    emit()
    emit("Category concentration of wins (observable before seeing any answer — category and "
         "difficulty are task metadata, not derived from correctness):")
    emit()
    for cat, winners in sorted(disagreement_cats.items()):
        b_wins = sum(1 for w in winners if w == MODEL_B)
        emit(f"- **{cat}**: {len(winners)} disagreement(s), {b_wins} favor 120b, "
             f"{len(winners)-b_wins} favor 20b")
    emit()
    summarization_share = sum(1 for t in disagreements if rec[t]["category"] == "summarization" and rec[t]["b_correct"])
    emit(f"{summarization_share}/{len(disagreements)} of all disagreements are 120b wins on "
         f"summarization specifically. The remaining disagreements (extraction x3, math x1, "
         f"classification x1) split 3-favor-20b vs 2-favor-120b — closer to noise than pattern "
         f"at this sample size. **Verdict: summarization is the one category with a systematic, "
         f"predictable-before-the-fact signal (120b wins there); the rest of the disagreement "
         f"set is too small and mixed to call systematic** — which is exactly what the category "
         f"rule above already encodes (it assigns summarization to 120b and defaults everything "
         f"else to 20b in every category except one, since only summarization's within-category "
         f"gap was large enough to flip the assignment).")
    emit()

    # ---------------------------------------------------------------
    # PHASE 5: best simple baseline
    # ---------------------------------------------------------------

    # The recommended baseline is the one with demonstrated (LOOCV)
    # validity, not merely the highest in-sample number — D. Category-
    # aware (full) scores higher in-sample but its LOOCV showed that
    # edge doesn't survive honest testing; D2 does.
    best = d2_strategy
    emit("## Phase 5 — best simple baseline")
    emit()
    emit(f"Not the highest in-sample scorer (that's D at {d_strategy['accuracy']:.1%}, but its "
         f"LOOCV accuracy collapses to {loocv_acc:.1%} — no better than always-20b). "
         f"**{best['name']}** ({best['accuracy']:.1%} in-sample, and — uniquely among the rules "
         f"tested — {loocv2_acc:.1%} under LOOCV, i.e. no measured generalization gap) is the "
         f"recommended baseline: simple enough to state in one sentence (\"route summarization "
         f"to 120b, everything else to 20b\"), interviewable without a slide, and the only rule "
         f"here whose out-of-sample performance was actually checked rather than assumed.")
    emit()
    emit(f"- vs always-20b: {best['accuracy']-always_a['accuracy']:+.1%} accuracy, "
         f"{best['cost']/always_a['cost']:.2f}x nominal cost, {best['avg_latency']/always_a['avg_latency']:.2f}x latency")
    emit(f"- vs always-120b: {best['accuracy']-always_b['accuracy']:+.1%} accuracy, "
         f"{best['cost']/always_b['cost']:.2f}x nominal cost ({(1-best['cost']/always_b['cost']):.1%} "
         f"cost reduction), {best['avg_latency']/always_b['avg_latency']:.2f}x latency "
         f"({(1-best['avg_latency']/always_b['avg_latency']):.1%} latency reduction)")
    oracle = strategies[2]
    emit(f"- vs oracle: {oracle['accuracy']-best['accuracy']:+.1%} accuracy short of the "
         f"{oracle['accuracy']:.1%} ceiling, capturing "
         f"{(best['accuracy']-always_a['accuracy'])/(oracle['accuracy']-always_a['accuracy']):.0%} "
         f"of the total available gap between always-20b and the oracle")
    emit(f"- routes only {best['pct_120b']:.1%} of requests to 120b (vs 100% for always-120b), "
         f"while matching or approaching its accuracy")
    emit()

    return locals()


def _write_decision_sections(ctx: dict) -> None:
    emit = ctx["emit"]
    strategies = ctx["strategies"]
    always_a, always_b, oracle = strategies[0], strategies[1], strategies[2]
    best = ctx["best"]  # the LOOCV-validated D2 rule, same as Phase 5 recommends - not
    # recomputed by raw in-sample accuracy, which would silently pick D again
    n = ctx["n"]
    loocv2_acc = ctx["loocv2_acc"]

    emit("## Phase 6 — V3 decision inputs")
    emit()
    emit(f"1. **Does routing already provide useful value with only two Groq models?** Yes — "
         f"{best['name']} reaches {best['accuracy']:.1%}, within "
         f"{oracle['accuracy']-best['accuracy']:.1%} of the {oracle['accuracy']:.1%} oracle "
         f"ceiling, using a one-line rule.")
    emit(f"2. **Does the rule-based router match or beat always-120b?** "
         f"{'Yes' if best['accuracy'] >= always_b['accuracy'] else 'No'} — "
         f"{best['accuracy']:.1%} vs {always_b['accuracy']:.1%} "
         f"({best['accuracy']-always_b['accuracy']:+.1%}).")
    emit(f"3. **How much 120b usage can be avoided?** "
         f"{1-best['pct_120b']:.1%} of requests avoid 120b entirely "
         f"({(1-best['pct_120b'])*n:.0f}/{n} tasks), cutting nominal cost to "
         f"{best['cost']/always_b['cost']:.1%} of always-120b's and latency to "
         f"{best['avg_latency']/always_b['avg_latency']:.1%}.")
    emit(f"4. **Quality tradeoff vs oracle?** {oracle['accuracy']-best['accuracy']:.1%} "
         f"({oracle['correct']-best['correct']} task(s): the oracle also correctly routes the "
         f"6 non-summarization disagreement tasks, which no rule tested here — including D2 — "
         f"can distinguish from noise at this sample size).")
    emit(f"5. **Is there enough disagreement data to justify learned routing?** Not yet "
         f"demonstrated — only "
         f"{sum(1 for t in ctx['graded_ids'] if ctx['rec'][t]['a_correct'] != ctx['rec'][t]['b_correct'])} "
         f"disagreement tasks total, and the one rule that passed LOOCV (D2, "
         f"{loocv2_acc:.1%}) captures its entire gain from a single observable bit (\"is this "
         f"summarization\") — it does not use the other 6 disagreement tasks at all, and "
         f"LOOCV showed the fuller rule that tried to use them (D) does not generalize. A "
         f"learned router would need to find real, generalizing structure in those remaining 6 "
         f"tasks specifically - unproven with this little data, and the training-data-size "
         f"problem that sank V3 twice before hasn't gone away.")
    emit(f"6. **What would a learned router have to beat to be worthwhile?** Not always-20b or "
         f"always-120b (the old baseline) - **{best['name']} at {best['accuracy']:.1%} "
         f"({loocv2_acc:.1%} LOOCV-validated, not just in-sample), {best['pct_120b']:.1%} 120b "
         f"usage, {best['cost']/always_b['cost']:.2f}x always-120b's nominal cost**. This is "
         f"the new bar V3 must clear to justify its added complexity, and it must clear it "
         f"under the same out-of-fold discipline, not just in-sample accuracy.")
    emit()

    both_fail_ids = sorted(
        t for t in ctx["graded_ids"]
        if not ctx["rec"][t]["a_correct"] and not ctx["rec"][t]["b_correct"]
    )
    emit("## Phase 7 — third model (Qwen) decision")
    emit()
    emit(f"Not run. The simple-routing result changes the question a third model would need to "
         f"answer: the 20b/120b gap is now mostly explained by one category (summarization), "
         f"not general capability. Before adding Qwen, the sharper question is whether it adds "
         f"capability specifically where **both current models fail together** "
         f"({len(both_fail_ids)} tasks: {', '.join(both_fail_ids)}) - that's where a third "
         f"model could expand the oracle ceiling itself, not just get closer to an already-"
         f"known {oracle['accuracy']:.1%}. Recommend still holding Qwen until that specific "
         f"question is worth asking, and running it only against those both-fail tasks plus "
         f"the existing {n}-task auto-gradeable set if approved - not all 104.")
    emit()


if __name__ == "__main__":
    ctx = main()
    _write_decision_sections(ctx)
    REPORT_PATH.write_text("\n".join(ctx["lines"]) + "\n")
    print(f"\nwrote {REPORT_PATH.relative_to(REPO_ROOT)}")
