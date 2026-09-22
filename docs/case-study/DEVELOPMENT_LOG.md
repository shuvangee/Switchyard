# Development log

A running, dated log of meaningful work sessions: what was done, what was
learned, what's next. This is the raw material the rest of the case study
gets distilled from — terser and more frequent than `PROJECT_STORY.md`.

## What belongs here

- One entry per meaningful work session (not every commit).
- What was attempted, what actually happened, and any surprises.
- Links to relevant commits/PRs where useful.

## Format

```
## YYYY-MM-DD — short title

What was done. What was learned. What's next.
```

## Log

## 2026-09-18 — Project bootstrap

Established the repository foundation before any product functionality:
directory structure (`frontend/`, `backend/`, `benchmarks/`, `experiments/`,
`docs/`, `scripts/`), a minimal FastAPI backend (health check only), a
minimal Next.js/TypeScript frontend (single status page), `CLAUDE.md`,
`PROJECT_STATE.md`, this case-study structure, root `README.md`,
`.gitignore`, and `.env.example`. No routing, provider, benchmarking, or
evaluation logic was implemented. Verified the backend starts and its
tests pass, and that the frontend builds. Next: design and implement V0
(model performance benchmarking).

## 2026-09-18 — V0: model performance lab

Built V0 end to end: SQLAlchemy persistence (benchmark tasks, model
configs, experiment runs, model executions); a `Provider` interface with a
mock provider (three deterministic, hash-seeded profiles — fast/cheap/
basic-skill, slow/pricier/capable-skill, flaky/error-prone) and a real
OpenAI adapter (disabled without `OPENAI_API_KEY`, never called live);
evaluation strategies (exact match, classification label, valid JSON,
manual) that clearly distinguish "not evaluated" from "evaluated and
failed"; a benchmark task loader that validates JSON files and syncs them
into the DB, plus 12 sample tasks across all 8 categories; an experiment
runner that executes every (task, model) pair, continues past individual
provider failures, and records latency/tokens/cost/evaluation; REST
endpoints for all of the above; and a frontend (Overview, Benchmarks,
Experiments) showing real data with honest empty states.

Three real bugs surfaced during provider testing, not while writing
production code but while writing tests for it: a greedy email regex that
swallowed trailing sentence punctuation, name extraction that matched the
instruction sentence's own capitalized first word ("Return...") instead of
the actual data after "for:", and an initial "chained math" design
(finding multiple regex matches and applying them in sequence) that turned
out not to work the way it looked like it would once a real prompt broke
the assumption of adjacent matches — replaced with a simpler and more
robust "does this profile's regex handle negatives/decimals" distinction.
See `FAILURES_AND_LESSONS.md`.

Verified end to end against the real (not test-client) server: a 36-
execution run (12 tasks x 3 mock models) completed with the mock-accurate
profile correct on 8/8 deterministically-evaluated tasks (higher latency,
higher cost), mock-fast correct on 4/8 (much lower latency/cost), and
mock-flaky producing simulated errors on some executions — the mechanism
V0 exists to prove works, demonstrated on the mock provider. This is
pipeline verification, not a research finding: no real model was involved,
so nothing here goes in `METRICS.md`/`EXPERIMENTS.md`, which stay empty
until real provider experiments are actually run.

Next: design V1 (rule-based routing) — but only once real experiments
against real providers have actually been run and looked at; V0's job was
to build the instrument, not to draw conclusions with it yet.

## 2026-09-18 — V1: rule-based router

Started by actually reviewing V0's evidence, which turned out not to
exist anywhere structured yet — `EXPERIMENTS.md`/`METRICS.md` were still
empty, and the only prior numbers were prose in this log. Wrote
`scripts/run_v0_baseline.py` to run every enabled model against every
benchmark task for real and committed the result to
`experiments/results/v0-mock-baseline.json` — this is real, measured
output (no OPENAI_API_KEY is configured, so mock provider only, stated
explicitly everywhere this evidence is cited). It showed a clean pattern:
on every easy extraction/classification/math/structured_output task,
`mock-fast-v1` matched `mock-accurate-v1`'s correctness (4/4 each) at
~7x lower latency and ~29x lower cost; on every medium/hard task in those
same categories, `mock-fast-v1` was wrong 4/4 times while `mock-accurate-v1`
was right 4/4. The four manual-eval categories (summarization/reasoning/
coding/debugging) have never been scored at all.

Built the V1 core from that evidence: `app/routing/analyzer.py`
(transparent heuristics — regex for math, short keyword lists per
category, word count for difficulty — explicitly not claiming to be a
real classifier), `app/routing/rules.py` (three rules, each citing the
specific baseline numbers behind it: easy-deterministic → fast,
medium/hard-deterministic → accurate, unscored-category → accurate as a
conservative default under genuine uncertainty), and
`app/routing/router.py` (first-match-wins, skips a rule whose target
model is disabled rather than breaking). `mock-flaky-v1` is never a
routing target — nothing in the evidence justifies it. Added
`RequestLogORM` + `app/routing/service.py` to persist every routed
request's full analysis/decision/execution as one row, and API endpoints
(`POST /route`, `GET /requests`, `GET /requests/{id}`) plus a
live-computed performance summary on `GET /models` (queried from actual
`model_executions`, never a fixed snapshot). Frontend: Playground,
Request History, and an actual Models page.

Verification (12 representative requests across all 8 categories, live
server) surfaced two real, distinct problems — not something to smooth
over, exactly the kind of thing this section exists to record:

1. **A genuine misrouting.** "What is -8 + 15?" (5 words) is estimated
   `easy` by the word-count difficulty heuristic and routed to
   `mock-fast-v1`, which answers `23` (wrong — its basic math regex
   ignores the leading minus sign). Rephrasing the identical problem with
   more surrounding words pushes it into `medium`, correctly routing to
   `mock-accurate-v1` and getting `7`. The router did exactly what its
   configured rules say to do; the difficulty *signal* feeding it is
   simply too weak to catch this. Left unpatched on purpose — see
   `DECISIONS.md` and `FAILURES_AND_LESSONS.md`.
2. **Mock execution not generalizing to open-ended phrasing.** A
   correctly-routed classification request got a generic fallback
   response instead of a label, because `MockProvider`'s classification
   heuristic only recognizes the literal "one of: X, Y, Z" phrasing used
   in the curated V0 benchmark tasks. The routing decision was right; the
   mock's own naive heuristic just wasn't built for freeform input.

Both are documented in `FAILURES_AND_LESSONS.md` rather than fixed,
because fixing either one honestly would mean either teaching the
analyzer MockProvider's specific internals (defeats the point once a real
provider exists) or building real NLP (out of scope for a rule-based
baseline). They're real limitations of V1, stated as such.

Next: V1 is a baseline to be superseded, not a finished router. V2 should
add confidence/escalation specifically because it can catch a case like
the math misrouting *after* a wrong answer rather than needing a perfect
difficulty prediction beforehand — and any of this should be re-evaluated
against real provider data the moment it exists, since every routing rule
here is still mock-provider evidence only.

## 2026-09-18 — V2: validation, confidence, escalation, and the request trace

Started by re-reading V1's own case study rather than assuming what it
said. The two documented V1 failures — the math misrouting and the
classification-phrasing garbage response — became V2's actual design
inputs, not hypothetical scenarios.

Built, in order: `evaluate/validation.py` (content-level checks inferred
from the request itself — math via independent recomputation,
classification via label-list membership, structured_output via JSON
parsing, extraction via email format — everything else honestly
`NOT_VALIDATED`, never guessed); confidence
(`routing/router.py:estimate_confidence`, a heuristic HIGH/MEDIUM/LOW
label, explicitly not calibrated, that can preemptively escalate before
any model is called); escalation
(`routing/rules.py:ESCALATION_TARGETS` + a bounded `MAX_ATTEMPTS=2` retry
loop in `routing/service.py` triggered by either a `ProviderError` or a
validation `FAILED`); and a structured request trace
(`routing/trace.py`, persisted as `RequestLogORM.trace_events`) recording
system events only — request_received, analyzed, routed, model_completed,
provider_error, validation, escalating, returned — never model reasoning.
Router version bumped to v2. Added `GET /analytics`, live-computed from
`request_logs`, and a Playground/Request History/Analytics UI built around
the trace as the primary artifact, not a chat transcript.

Then actually ran the two V1 failure prompts through the real, unmocked
pipeline rather than assuming the fix worked:

- **The math case (fixed).** `"What is -8 + 15?"` still gets `23` from
  `mock-fast-v1` first — but validation independently computes `7`, flags
  the mismatch, escalates to `mock-accurate-v1`, which answers `7`, which
  validates. Real, measured cost: attempt_count=2, ~650ms extra
  wall-clock latency, one extra (pricier) model call. See `EXPERIMENTS.md`
  for the full before/after table.
- **The classification case (not fixed, and said so).** The same
  phrasing-dependent gap that broke `MockProvider`'s classification also
  breaks its validator — both key off the exact same `"one of:"` pattern.
  No pattern found → `NOT_VALIDATED`, not `FAILED` → no escalation
  triggers → the same garbage response from V1 is still returned in V2.
  This is the honest negative result of the version: escalation is only
  as good as validation's ability to detect a problem in the first place.

A third, unplanned finding surfaced while verifying the second case:
routing a classification prompt that *does* have `"one of:"` phrasing to
`mock-fast-v1` returned `"positive"` for a review saying "disappointing"
— arguably wrong, but `validation_status: passed`, because `"positive"`
is genuinely a member of the allowed label set. Validation checks
structural membership, not semantic correctness, for any category without
real ground truth. Recorded in `EXPERIMENTS.md` and `DECISIONS.md` rather
than treated as a bug — there's no way to check semantic correctness
without an answer key that doesn't exist for freeform input.

Also found, while capturing real numbers for the case study rather than
estimating them: `RequestLogORM.latency_ms`/`estimated_cost_usd` only
capture the *final* attempt of an escalated request, not the sum across
attempts. True wall-clock latency for the math case was ~763ms; the
persisted value is 653ms. Flagged in `DECISIONS.md` as a known,
unresolved gap in the analytics rather than silently left inconsistent.

Next: before V3 (learned routing), the highest-value step is still what
V1 deferred — real experiments against a real provider. Every number in
this version's `EXPERIMENTS.md` entries is genuine but mock-only; V2's
validation/escalation *mechanism* is real, but whether it's solving a
real problem (vs. a problem specific to how MockProvider is built) is
still unmeasured.

## 2026-09-19 — Second real provider adapter: Gemini

Added `GeminiProvider` (`backend/app/providers/gemini_provider.py`),
following the exact shape of `OpenAIProvider` — plain `httpx` call to
Google's `generateContent` endpoint, `ProviderError` on any failure,
disabled without `GOOGLE_API_KEY`. Registered as `gemini-2.0-flash` in
`registry.py` (pricing marked provisional — converted from Google's
published rate, not yet confirmed against a real bill). Added
`test_providers_gemini.py` (mirrors `test_providers_openai.py`, no real
network calls — `httpx.post` monkeypatched) and two registry tests for
the enabled/disabled-without-key behavior. 136 backend tests pass (up
from 130).

This closes the last structural gap before running real experiments: the
codebase can now, in principle, call two different real providers behind
the same interface, which is the actual point of the adapter pattern (see
`DECISIONS.md`, "Provider adapter interface before any real provider
integration"). No real Gemini call has been made in this environment —
only mocked HTTP responses are exercised by tests. Running it for real
still requires: a valid `GOOGLE_API_KEY` in a local, gitignored `.env`,
and a pre-run cost estimate (request count × Gemini's per-token pricing)
before spending anything, per CLAUDE.md's cost-constraint rule.

Next: unchanged from V2's close — the highest-value step is still running
real experiments (now possible against OpenAI or Gemini) and looking at
what the results actually show before touching V3.

## 2026-09-20 — First real-provider experiment, and what it actually revealed

Ran the 12 benchmark tasks for real against Gemini for the first time —
the "smallest practical step" toward real data, deliberately not V3.
Verified the adapter statically first (key loads, provider enabled), then
got explicit cost approval before any live call, per CLAUDE.md's
cost-visibility rule.

Getting a working model id took three tries. `gemini-2.0-flash` (what was
registered on 2026-09-19) 404'd — a live models-list call showed it isn't
in this account's model set at all. Switched to `gemini-2.5-flash`
(cross-checked pricing via web search, since `ai.google.dev` is blocked
by this environment's network policy) — also 404'd, this time with
Google's own error naming the replacement: `gemini-3.6-flash`. That one
worked. Each dead end cost genuinely $0.00 (a 404 happens before any
generation), and each swap was committed as its own `fix:` — see git log.
Also fixed, found in passing: `.gitignore` never actually matched the
project's real dev-DB filename (`switchyard.db`), only a generic
`db.sqlite3` pattern that doesn't apply here.

Added retry-with-backoff to `scripts/run_gemini_baseline.py` after the
first full run hit real rate limits (`429`, 5/12 tasks) and one transient
`503` — genuine real-provider failure modes the mock never modeled, since
it doesn't simulate rate limiting. Final result: **12/12 tasks succeeded**,
$0.00157 real cost, 334 input / 353 output tokens, ~3.7s avg latency.
Saved permanently at `experiments/results/gemini-3.6-flash-baseline.json`
(committed, not a throwaway dev DB — this one is meant to persist).

The actual headline finding wasn't about Gemini. Of the 8
deterministically-scored tasks, the automated evaluator marked only 3
`correct` — reading the raw response text, all 8 were substantively
right. `evaluate_exact_match` needs the whole response to equal the
expected string with no tolerance for a real model restating the
question; `evaluate_valid_json` calls `json.loads()` on the raw response
with no markdown-fence stripping, so a completely normal
` ```json ... ``` ` wrapper fails parsing outright. Both were written and
tested exclusively against `MockProvider`'s deliberately bare output
style, and the bug was invisible through all of V0/V1/V2 because nothing
but the mock had ever been evaluated. This is exactly the leakage
argument from the 2026-09-19 V3 data-readiness review, now demonstrated
with a real model rather than argued abstractly: V0's "quality" scores are
a function of matching the mock's format, not of real correctness. Full
per-task detail in `FAILURES_AND_LESSONS.md`; not fixed in this session
since it wasn't this run's scope, and fixing it responsibly needs a real
tolerance policy decided deliberately, not a one-line patch.

Next: fix the evaluator format-sensitivity (top of `PROJECT_STATE.md`'s
next objective) before trusting any future real-provider quality number —
otherwise every real model will look artificially worse than the mock,
which would be a materially misleading basis for V3 or any routing
decision. Running more real-provider data is still valuable but shouldn't
happen on top of a known-broken scorer.

## 2026-09-20 — Evaluator fix, then V3 reconsidered and held, then Phase 1 of data collection

Fixed the evaluator bug from the entry above: `evaluate_exact_match` now
falls back to a word-bounded token match when whole-string equality
fails; `evaluate_valid_json` retries once with a markdown code fence
stripped. Verified with zero new API calls — `scripts/rescore_evaluator_fix.py`
regenerated the 36 mock responses (deterministic, not a real call) and
reused the 12 real Gemini responses already captured, re-scoring all 48
against the fixed strategies: exactly the 5 diagnosed rows changed,
`incorrect` → `correct`, zero regressions. 140 tests pass.

Then asked directly to proceed to V3 anyway. Rather than silently comply
or silently refuse, laid out three concrete options (collect more data
first; run V3 now as an honest negative-result experiment on the current
thin data; build V3 infrastructure without training yet) and let the
decision be made explicitly — chose to collect more data first, keeping
V3 at zero lines of code, consistent with three separate data-readiness
reviews this session.

Started that data collection: expanded `benchmarks/tasks/` from 12 to 44
(4 new tasks per category), with real `expected_output` values for the
4 auto-scored categories and a written grading rubric in `metadata.notes`
for the 4 manual categories, since the user chose manual grading over an
LLM-judge for those. All 44 validated via the real loader before use.

**A real incident happened while regenerating the mock baseline.**
Re-running `scripts/run_v0_baseline.py` — previously always free, since
it selected models by `enabled` and no real provider used to be enabled —
silently made 44 real Gemini calls with no cost estimate or approval,
because `GOOGLE_API_KEY` now exists in `.env` from the 2026-09-19 work.
42 calls hit rate limits and errored (no retry logic in this script);
2 succeeded, for a real cost of $0.0000585. It also overwrote the
historical `v0-mock-baseline.json` with mixed real/mock data. Caught via
`git diff --stat` showing a ~2,000-line change before doing anything
else with the output; restored the file from git (safe — regenerable
committed history) and fixed the actual bug: the script now filters by
`provider == "mock"` explicitly rather than `enabled`, so this class of
mistake can't recur regardless of what gets added to `.env` later. Full
incident write-up in `FAILURES_AND_LESSONS.md`. Regenerated the mock
baseline cleanly afterward — 132 rows (44 tasks × 3 mock models), $0 real
cost, 140 tests still passing.

Next: Phase 2 (manual grading of the 4 previously-unscored categories)
and Phase 3 (real-provider experiments on the expanded set, cost estimate
first) are both unstarted.
