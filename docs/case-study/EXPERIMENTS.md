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

All entries below use the mock provider (no `OPENAI_API_KEY` configured
in this environment) — stated on every entry, not just here. They measure
how the Switchyard *pipeline* behaves (routing, validation, escalation
mechanics), not real-model quality/cost/latency. Real-provider experiments
are the next objective in `PROJECT_STATE.md`.

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
