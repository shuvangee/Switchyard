# Experiments

A record of actual experiment runs: what was measured, against which
benchmark tasks, providers, and routing strategy, and what the results
were.

## What belongs here

- One entry per experiment run (or meaningfully grouped set of runs).
- Exact configuration: router version, providers/models involved,
  benchmark task set, evaluation method.
- Real, measured results — numbers copied from `experiments/results/`,
  never estimated or rounded to look cleaner.
- Interpretation: what the result does and does not show.

## Rule

Nothing goes in this file until an experiment has actually been run. No
placeholder numbers, no illustrative examples with made-up data.

## Status

Entries before 2026-09-20 all use the mock provider (no `OPENAI_API_KEY`
configured in this environment) — stated on every such entry, not just
here. They measure how the Switchyard *pipeline* behaves (routing,
validation, escalation mechanics), not real-model quality/cost/latency.
The 2026-09-20 entry below is the first entry backed by a real (non-mock)
provider call.

## Log

## 2026-09-18 — V2 validation/escalation fix for the V1 math misrouting

**Problem:** V1 routed `"What is -8 + 15?"` (estimated difficulty=easy by
word count) to `mock-fast-v1`, which answered `23` (wrong — its regex
ignores the leading minus sign) and returned it marked `status: success`,
indistinguishable from a correct response.

**Why it happened:** V1 had no mechanism to check response *content* —
only whether the provider call itself succeeded. See
`docs/case-study/FAILURES_AND_LESSONS.md` (2026-09-18, word-count
difficulty entry) for the full root cause.

**What we changed:** Added `evaluate/validation.py` (independently
recomputes simple arithmetic from the prompt and compares) and escalation
in `routing/service.py` (a validation `FAILED` outcome retries with
`mock-accurate-v1`).

**Result, measured on the real (unmocked) pipeline, same prompt:**

| | V1 | V2 |
|---|---|---|
| Final answer | `23` (wrong) | `7` (correct) |
| Marked as | `success` | `success`, `validation_status: passed`, `escalated: true` |
| Attempts | 1 | 2 |
| Latency (winning attempt) | 110ms (`mock-fast-v1`) | 653ms (`mock-accurate-v1`) |
| True wall-clock latency | 110ms | ~763ms (110ms wasted + 653ms) — see the "only final attempt recorded" entry in `DECISIONS.md`; `latency_ms` on the row is 653ms, not 763ms |
| Cost (winning attempt) | ~$0.0000015 (`mock-fast-v1`, from the V0 baseline's per-call average) | $0.000024 (`mock-accurate-v1`) |

**Interpretation:** Quality went from wrong-but-confident to correct, at
the cost of one extra model call (~+650ms wall-clock, ~16x the per-call
cost of the fast tier alone for this prompt). This is a real, measured
trade — not a claim that escalation is "free" or that it always helps
(see the classification entry below, where it doesn't). It is still mock-
provider evidence: the *mechanism* (validate, detect mismatch, retry
with a stronger model, get a better answer) is real and reproducible;
whether a real model pair shows the same fast-wrong/accurate-right split
is unmeasured.

## 2026-09-18 — V2 does NOT fix the V1 classification phrasing failure

**Problem:** V1's Playground example — `"Classify the sentiment of this
review as positive, negative, or neutral."` (no `"one of: X, Y, Z"`
phrasing) — got `MockProvider`'s generic fallback string back instead of
a label.

**Why it happened:** `MockProvider._try_classification` only recognizes
the literal `"one of:"` pattern; without it, no model profile can produce
a label at all, regardless of skill level.

**What we changed:** Added classification validation
(`evaluate/validation.py:_validate_classification`) — but it has the
*same* dependency: it can only check a response against a label list it
extracted from the prompt via the same `"one of:"` pattern.

**Result, measured on the real (unmocked) pipeline, same prompt:**
`validation_status: not_validated` ("no explicit label list found in
prompt") — not `failed`. No escalation is triggered (only a `FAILED`
outcome escalates), so the same garbage fallback response from V1 is
returned unchanged in V2.

**Interpretation:** This is the honest, important negative result of this
version: escalation only helps when validation can actually *detect* a
problem. When the request itself lacks the structure needed to check the
response (here, an explicit label list), V2 has no more information than
V1 did, and correctly declines to guess rather than escalate on a false
signal. Fixing this needs either a smarter validator (e.g. inferring
labels from context without explicit phrasing — real NLP, out of scope)
or a smarter mock (same problem, one layer down) — not more escalation.

## 2026-09-18 — Discovered while testing: "valid label" is not "correct label"

**Problem, found incidentally while verifying the entry above:** routing
`"Classify sentiment. Respond with exactly one of: positive, negative,
neutral. Review: The service was disappointing."` to `mock-fast-v1`
returned `"positive"` — `"disappointing"` is in the capable profile's
negative-word lexicon but not the basic profile's, so `mock-fast-v1`
found no keyword match and defaulted to the first listed label.
`validation_status` was `passed`, because `"positive"` genuinely is one
of the three allowed labels.

**Why it happened:** Classification validation checks label-list
*membership* (a real, mechanical check with no ground truth needed) —
it cannot check semantic correctness (whether `"positive"` is the *right*
label for this specific review) without a known-correct answer, which
freeform Playground requests never have.

**What we changed:** Nothing — recorded as a scope boundary, not a bug.
Math validation has genuine ground truth (arithmetic is computable from
the prompt alone); classification does not, for a category with no
author-assigned expected label. Consistent with CLAUDE.md: "do not pretend
every open-ended request can be automatically proven correct."

**Result:** `validation_status: passed` here means "structurally a valid
answer," not "correct." Worth remembering when reading `validation_passed`
in `RoutingAnalytics` — it is not a proxy for "the router got it right,"
except for categories (math, JSON) where passing genuinely implies
correctness.

## 2026-09-20 — Switchyard's first real-provider experiment: Gemini 3.6 Flash

**Configuration:** `scripts/run_gemini_baseline.py`, the 12 existing
benchmark tasks (unchanged from V0), one real model —
`gemini-3.6-flash` via `GeminiProvider` — no mock models in this run,
no routing (this bypasses `POST /route` entirely and calls the
provider/experiment layer directly, same as `run_v0_baseline.py` does).
Output capped at 512 tokens/call. Full raw output:
`experiments/results/gemini-3.6-flash-baseline.json`.

**Getting here took three model ids** (`gemini-2.0-flash` and
`gemini-2.5-flash` both 404'd — retired for this account) — see
`FAILURES_AND_LESSONS.md` for the full story. The initial 12-call attempt
also hit `429 Too Many Requests` on 5 tasks (a real free-tier rate limit,
not a bug) and one `503 Service Unavailable` (a transient server error) —
both resolved by retrying with backoff, now built into the script.

**Result — measured, not estimated:**

| | Value |
|---|---|
| Tasks run | 12/12 |
| Succeeded (after retries) | 12/12 |
| Failed permanently | 0 |
| Total input tokens | 334 |
| Total output tokens | 353 |
| Total real cost | **$0.00157** |
| Avg latency (successful calls) | ~3,700 ms |
| Deterministically-scored tasks marked `correct` by the evaluator | 3/8 |
| Deterministically-scored tasks manually verified as substantively correct | 8/8 |

**Interpretation:** The gap between "3/8 marked correct" and "8/8 actually
correct" is not a Gemini quality finding — every deterministically-scored
task got a right answer. It is an evaluator-design finding: `exact_match`
and `valid_json` (`backend/app/evaluation/strategies.py`) require an exact
whole-string match / a fence-free JSON payload respectively, which
`MockProvider` was built to produce and a real conversational model is
not. See `FAILURES_AND_LESSONS.md` (2026-09-20) for the full per-task
breakdown and why this isn't patched in this session.

On cost and latency, this single real run is honestly not comparable yet
to the V0 mock baseline's per-model numbers — that comparison needs the
mock and a real model run under the *same* evaluator and ideally the same
task set repeated more than once (avg latency here, ~3.7s, is 5-70x every
mock profile's latency, which is expected and not itself a finding: mock
latency was simulated, this is a real network round trip). What this run
does establish, for the first time in this project: the Gemini adapter
works end to end against the live API, real token/cost accounting flows
correctly through the existing experiment pipeline unmodified, and the
project's evaluation layer has a real, previously-invisible bug that
every future real-provider comparison needs to account for.

## 2026-09-22 — V3: a learned router was built, trained, and evaluated — it loses

**Context:** three separate data-readiness reviews (2026-09-19 and twice
restated) concluded the existing dataset was too small to responsibly
train a learned router, and recommended collecting more real data first.
That data collection (benchmark expansion to 44 tasks, manual-grading
generation) is still in progress and partially blocked (Gemini's
20-requests/day free-tier quota, and a token-cap bug that made 18 of 20
manual-category responses unusable — see `FAILURES_AND_LESSONS.md`,
2026-09-20 and 2026-09-21). Asked directly to build V3 anyway rather than
continue waiting, the approach taken here was: build the real pipeline,
train on the real (if thin) data that already exists, and report exactly
what happens — including if the result is negative. It is negative.

### Data used

Every row with a deterministic evaluator across the two experiment result
files that exist in this repo:
- `experiments/results/v0-mock-baseline.json` — 44 tasks × 3 mock models.
- `experiments/results/gemini-3.6-flash-baseline.json` — 12 tasks × 1 real
  model (gemini-3.6-flash), **re-scored in place** to fix the 5 rows the
  evaluator bug had mismarked (see `FAILURES_AND_LESSONS.md`, 2026-09-20)
  — this session also caught and fixed that the corrected scores had
  never actually been written back to the committed file; they were only
  verified in-memory by `scripts/rescore_evaluator_fix.py` and never
  persisted. Training on the stale file would have silently used wrong
  labels.

The 4 manual-eval categories (coding, debugging, reasoning, summarization
— 20 of the 44 tasks) contribute **zero** rows: there is no ground truth
to check "correct" against for them, and building one would mean either
guessing or waiting on the still-blocked manual-grading work. Excluding
them is not a bug — see "Training target" below for why a fabricated
label would be worse than no row at all.

### Data limitations (stated up front, because they explain the result)

- **24 total training rows** — one per task with a deterministic
  evaluator and at least one candidate that got it right.
- **Almost entirely mock-provider evidence.** Only 12 of the 24 rows have
  a real-provider (Gemini) candidate at all; the other 12 only ever saw
  mock models. Whatever pattern exists in most of this data is a
  property of `MockProvider`'s own regex heuristics, not of real model
  capability — the exact leakage risk the 2026-09-19 review raised,
  unresolved by construction (this dataset didn't get bigger, only more
  precisely labeled).
- **Severe class imbalance.** Target distribution: `mock-fast-v1` 14,
  `mock-accurate-v1` 8, `gemini-3.6-flash` 2.
- **The feature signal itself is noisy**, discovered while building this:
  category is computed by the same heuristic analyzer the router uses at
  inference time (`analyze_request`), not the task's authored ground
  truth — deliberately, to avoid train/serve skew (see Decisions below).
  But that means 4 of the real `extraction` tasks get heuristically
  categorized as `reasoning` instead, because their prompts don't contain
  the literal word "extract." The training data is honestly exactly as
  noisy as what the router sees for real, which is the point — but it
  means the *inputs*, not just the *sample size*, limit what's learnable.

### Training target — definition and why

**The cheapest candidate model with a recorded CORRECT outcome for each
task.** This directly encodes the research question (can a router pick a
cheaper model without losing correctness) as a single per-task label,
computed from real recorded `evaluation_status`/`estimated_cost_usd`
values, never invented. A task where no candidate got it right
contributes no row — there is no "correct and cheap" choice to learn
there, and assigning one anyway (e.g., "the least-wrong option") would be
fabricating a label CLAUDE.md explicitly forbids. In this dataset every
task had at least one correct candidate, so this exclusion path was
defined but never actually triggered (`no_correct_candidate: 0`).

### Features considered and selected

Selected: **category** (one-hot, from the heuristic analyzer),
**difficulty** (ordinal, same source), **structured_output_required**
(bool, already computed by the analyzer), **estimated_input_tokens**
(the one continuous signal available). All four are already produced by
`routing/analyzer.py` for the rule-based router — a learned router using
different inputs than V1 would make the comparison unfair.

Considered and rejected: **embeddings** — no justification at N=24;
fitting anything on top of a high-dimensional embedding with this few
examples is guaranteed to overfit, and it adds real inference-time cost
and latency for a benefit nothing here can demonstrate.
**Historical per-model performance** — would need a real, sizeable
request history to be anything but the same 24 rows restated; no such
history exists (V1/V2 request logs are never persisted outside ephemeral
dev databases).

### Pipeline

```
experiments/results/*.json  (raw data)
        |
routing/learned/dataset.py   (dataset construction — one row per task,
        |                      target = cheapest correct candidate)
routing/learned/features.py  (feature processing — category/difficulty/
        |                      structured-flag/token-count, via the same
        |                      heuristic analyzer used at inference time)
        |
leave-one-out cross-validation   (NOT a train/val/test split — see below)
        |
routing/learned/train.py     (baseline comparison, final-model fit on
        |                      all rows, artifact + manifest saved)
        v
routing/learned/artifacts/learned-v1.{joblib,manifest.json}
```

**Why leave-one-out, not a train/val/test split:** a conventional 80/20
split on 24 rows leaves a ~5-row test set, where getting one row's
prediction right or wrong swings "accuracy" by 20 points — a single such
split's number would be close to meaningless. Leave-one-out (train on 23,
predict the 1 held out, repeat 24 times, using every row as a held-out
test exactly once) is the standard, defensible method for a dataset this
small — not an improvised workaround. It prevents leakage the same way a
split does: each held-out row's prediction never saw that row's own label
during its training.

**Selected algorithm:** a depth-2 `DecisionTreeClassifier`
(scikit-learn, `min_samples_leaf=2`) — chosen for interpretability (the
whole tree is printable and human-readable, matching the project's
existing "explainable over merely accurate" stance for V1) and because a
model this simple is honest about what 24 rows can actually support; a
deeper tree or a higher-capacity model (gradient boosting, a neural net)
would fit noise faster, not signal better, at this sample size.
**Alternative considered:** logistic regression — rejected only because a
decision tree's split structure is more directly comparable to reading
V1's own if/else rules, which is the actual comparison this experiment
needs to make.

**New dependency:** `scikit-learn` + `joblib` added to
`backend/requirements.txt` — the first ML dependency in this project,
justified because building an actual learned model is V3's whole point;
not applicable to CLAUDE.md's "heavy infrastructure" clause (that's about
Kubernetes/queues/Redis, not a training library scoped to exactly this
task).

### Baselines and results

Full table: `experiments/results/learned-v1-comparison.md` (generated by
`scripts/report_v3_comparison.py` from the training manifest — no new
predictions made, just formatted).

| Strategy | Accuracy (evaluable) | Avg cost/task | Total cost | Unevaluable |
|---|---:|---:|---:|---:|
| **learned-v1** | **56.5%** | **$0.000013** | $0.000310 | 1/24 |
| always-cheapest (mock-fast-v1) | 58.3% | $0.000002 | $0.000058 | 0/24 |
| always-strongest (mock-accurate-v1) | 95.8% | $0.000073 | $0.001755 | 0/24 |
| V1/V2 rule-based router | 75.0% | $0.000041 | $0.000986 | 0/24 |
| random (expected value over each task's actual candidates) | 72.9% | $0.000032 | $0.000772 | 0/24 |

"Unevaluable" rows are where a strategy picked a model with no recorded
outcome for that specific task (e.g., predicting `gemini-3.6-flash` for
one of the 12 mock-only tasks) — reported as unknown, never guessed as
correct or incorrect, consistent with how every other honesty rule in
this project works.

### Result: learned-v1 does not beat the rules — stated plainly

**No, it does not beat V1's rule-based router (56.5% vs 75.0%), and it
does not beat random selection (56.5% vs 72.9%). Worse: it is strictly
dominated by the trivial `always-cheapest` baseline — lower accuracy
(56.5% vs 58.3%) at *higher* cost ($0.000013 vs $0.000002 avg/task, ~5.5x
more expensive).** A router that is both less accurate and more expensive
than "always pick the cheapest model and don't think about it" has
negative value over doing nothing. This is not a close call requiring
interpretation — it is a clear loss on every axis that matters.

### Failure analysis — why, specifically

1. **Not enough data, exactly as predicted.** 24 rows, 3 classes, one
   class (`gemini-3.6-flash`) with only 2 examples. A depth-2 tree has at
   most 4 leaves; with this little data each leaf's class distribution is
   dominated by whichever few rows happened to land in it, not a real
   population pattern. This is the textbook failure mode the three prior
   data-readiness reviews described in the abstract, now reproduced
   concretely.
2. **`always-strongest`'s 95.8% is the real signal in this data, and the
   learned model didn't find it.** Most tasks in this dataset are solved
   correctly by `mock-accurate-v1` — the actual learnable pattern here is
   closer to "the capable tier is usually right," not the more nuanced
   "route cheap when safe" story V1's rules encode. A model that could
   only ever say "always pick the accurate one" would have beaten
   `learned-v1` by 39 points. That the tree didn't converge on something
   closer to that, even as a crude default, reflects how little a
   depth-2 split on 24 noisy rows can actually resolve.
3. **The feature noise compounds the sample-size problem.** With 4 of 24
   rows' category feature already wrong (the extraction-mislabeled-as-
   reasoning issue above), a model that memorizes rather than
   generalizes doesn't even have consistent inputs to memorize against.
4. **This is a data problem, not a pipeline bug** — verified directly:
   `test_learned_v1_recovers_the_unambiguous_synthetic_pattern`
   (`backend/tests/test_learned_train.py`) runs the identical pipeline
   against a synthetic dataset with a genuinely learnable, noise-free
   pattern and gets ≥90% leave-one-out accuracy. The mechanism works;
   the real data doesn't currently support it.

### What this does and doesn't mean for V3

The pipeline is real, tested (167 backend tests, up from 146), and
functional end to end — `router_version="learned-v1"` is a real,
selectable strategy in `POST /route`, recorded per request exactly like
`v2` is. What doesn't exist is a reason to prefer it: on the only honest
evaluation available, it loses to a strategy with zero intelligence
(`always-cheapest`) and to the rules it was supposed to improve on. It is
wired up for future comparison, explicitly not recommended for real
traffic, and the router selection mechanism itself defaults to `v2`
unless `learned-v1` is explicitly requested.

This does not mean learned routing is a dead end for Switchyard — it
means the data collection work already in progress (Phase 2/3, still
blocked on Gemini's daily quota) is not optional groundwork to skip past;
it is the actual blocker, now demonstrated rather than argued. The honest
recommendation is the same one the 2026-09-19 review gave: get more real
data, across more of the categories, before expecting a learned router to
outperform three lines of if/else.
