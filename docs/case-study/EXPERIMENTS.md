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
