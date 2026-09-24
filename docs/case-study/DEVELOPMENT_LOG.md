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

## 2026-09-22 — V3 built, trained, and evaluated: an honest negative result

Built the full learned-routing pipeline end to end: dataset construction
(`backend/app/routing/learned/dataset.py`), feature encoding, leave-one-
out cross-validation, baseline comparison, and a saved router artifact
(`learned-v1.joblib` + manifest), wired into `POST /route` as a
selectable `router_version` alongside `v2` (which stays the default).
21 new tests (167 total, up from 146).

Trained on the 24 real rows available at the time (mock + the one real
Gemini experiment). Result: 56.5% leave-one-out accuracy, strictly
dominated by "always pick the cheapest model" (58.3%, at 5.5x lower
cost), and behind both random (72.9%) and V1's rules (75.0%). Verified
this is a data problem, not a pipeline bug, via a synthetic-data control
test that recovers ≥90% accuracy on the identical code path when the
underlying pattern is genuinely learnable. Full analysis in
`docs/case-study/EXPERIMENTS.md` (2026-09-22 entry).

## 2026-09-22/23 — Second benchmark expansion (44→104 tasks), GroqProvider, 4 real bugs fixed, GitHub reconciled

Expanded `benchmarks/tasks/` again, 44 → 104 (13 per category), this
round deliberately including harder cases per category and going
through a full review-and-revise cycle with the user before writing
anything: test cases added to every coding task for a future test-
execution grader, 5 reasoning tasks converted to `exact_match` with
verified answers, `is_anagram`'s prompt disambiguated, and 5 debugging
prompts revised to request a parseable fenced code block.

Built `GroqProvider` (`openai/gpt-oss-20b`/`120b`, OpenAI-compatible,
mirrors the Grok/OpenAI adapter pattern) and, separately, fixed 4 real
bugs an automated Codex review found on the resulting PR: a provider
error on an escalation attempt could overwrite an already-completed
response with `None` (losing the "return the best attempt" contract);
only the final attempt's cost/latency was recorded across a validation-
triggered escalation, dropping an earlier billed call's cost from
analytics; all four provider adapters called `response.json()`
unguarded, risking an unhandled exception on a malformed 2xx body;
Gemini's thinking tokens weren't counted toward billed output. All four
fixed with regression tests that were confirmed to actually fail against
the pre-fix code before trusting them.

Also discovered and reconciled a real git-history split: `main` and this
session's branch had independently scaffolded the project from the same
initial commit (an earlier, separately-merged PR had put a minimal
bootstrap on `main`), so a second PR from this branch showed as
unmergeable. Verified this branch's content was a strict superset of
`main`'s in every overlapping file, merged non-destructively, and pushed
`main` up to date with the full V0–V3 build.

## 2026-09-23 — Groq data collection, V3 retrained, and two evaluation-methodology bugs caught

Attempted the 104-task x 2-Groq-model benchmark run from inside this
project's Claude Code sandbox — every call failed identically with a
network-level `403` before reaching Groq at all (this environment's
egress policy blocks `groq.com` outright, confirmed via the proxy status
endpoint). Walked the user through running the same, unmodified script
from their own machine instead: 208/208 calls succeeded, $0 real cost.
Full incident write-up in `FAILURES_AND_LESSONS.md`.

Wired the new data into V3's dataset (`DEFAULT_RESULT_FILES`) and
regenerated the mock baseline (free, mock-only) against all 104 current
tasks — it had gone stale at 44. Training rows: 24 → 56.

Retrained V3. The first result looked like a clean win (88.2% vs. 58.3%)
and wasn't: the two numbers were computed over different, non-
overlapping-in-size subsets of rows, because the `always-cheapest`/
`always-strongest` baselines were hardcoded to specific mock model ids
that had gone stale. Fixed (dynamic baseline selection by registry
price, common evaluable-row count for every strategy) and re-ran: 75.0%
vs. a fairly-computed 44.6%/64.3%/53.6%/67.8% — still not the full
picture. Checking every individual candidate model as its own trivial
baseline (not just the two named ones) found `always-groq-gpt-oss-20b`
at 89.3%, beating the learned model. A second small bug (the "best
baseline" picker briefly favored a baseline evaluated on only 8 of 56
rows) was caught and fixed before being reported. **V3 still loses** —
the specific baseline that dominates changed with more data, whether one
does did not. Full writeup: `EXPERIMENTS.md` and
`FAILURES_AND_LESSONS.md` (2026-09-23 entries).

## 2026-09-23 — Sandboxed code grading, then a routing-opportunity analysis before more training

Built `backend/app/evaluation/sandbox.py`, a real (kernel-enforced, not
assumed) sandboxed code-execution grader, and graded the 13 coding + 5
revised debugging tasks' real Groq responses. First run: 33/36 - turned
out to be a bug in the grader itself (extracting the pre-fix code block
shown before a debugging response's actual fix), not the model. Fixed,
re-ran: 36/36. Applied to `evaluation_status` in the results file as an
evaluation-quality fix, explicitly not wired into V3's training pipeline
(`evaluation_type` unchanged, row count confirmed unchanged at 56).

Then, before any further V3 training, ran a routing-opportunity analysis
asking a prior question: does `groq-gpt-oss-20b` vs `120b` even have a
real quality gap for a router to exploit? On the 75 of 104 tasks with
real ground truth, always-20b and always-120b tie exactly (68/75 each) -
a perfect oracle router tops out only 4.0 points above either, on just 6
disagreeing tasks, while 120b costs 1.87x the tokens and 1.51x the
latency. This reframes V3's repeated losses: they may not (only) be a
data-volume problem - this specific model pair may simply be too similar
in capability, on this task distribution, for routing to have much room
to help. Full analysis: `EXPERIMENTS.md` (2026-09-23) and
`experiments/results/routing-opportunity-analysis.md`.

## 2026-09-23 — V2.6 Phase 1/2 kickoff: evaluation coverage and a stronger-model proposal

Reframed the next stage explicitly as V2.6 - Evaluation Coverage &
Routing Opportunity Expansion, not another V3 retrain. Goal: find out
whether the 4-point routing ceiling is a property of the gpt-oss-20b/
120b pair specifically, or of the routing problem generally, without
changing the benchmark to manufacture a bigger gap.

Phase 1 progress on the 29 ungraded tasks: converted 3 reasoning tasks
(001/002/003) to `exact_match` where the answer was already single and
unambiguous, no prompt change needed - though scoring them is still
pending a response-text export from the user's local db, same gap as
before. Proposed (not written) revised prompts + test_cases for the
remaining 8 debugging tasks, mirroring the 009-013 precedent exactly,
including deliberately NOT resolving debugging-007's known spec
ambiguity just to make it easier to grade. Compared 4 evaluation
approaches for summarization (human rubric, LLM-judge, reference-based
metrics, hybrid) and recommended a deterministic required-fact presence
check derived from the existing rubrics, over LLM-as-a-judge, as the
primary signal - full comparison in `DECISIONS.md`.

Phase 2: registered `gemini-3.1-pro-preview` (reuses GeminiProvider,
already-configured key, no new provider code) as the proposed stronger-
capability contrast against groq-gpt-oss-20b. Estimated cost from real
Groq-run token counts as a proxy (~$0.40 for all 104 tasks, ~$2.60
worst case) - registration only, no live call, waiting on explicit cost
approval before Phase 3 can run.

## 2026-09-23 — Pivoted to Groq-only; finished V2.6 Phase 1's evaluation coverage

Explicit instruction: keep Switchyard zero-cost, Groq-only, no Gemini/
OpenAI/Anthropic calls. `gemini-3.1-pro-preview` stays registered
(unused) but is no longer part of the plan.

Finished the bulk of Phase 1 that a prior pass had only proposed:

- Revised 7 of the 8 legacy debugging tasks (001-006, 008) with test
  cases, each verified via the sandbox grader against BOTH the seeded
  buggy code AND a correct fix before being committed - caught one real
  bug in my own test case (`second_largest([5,3,8,1])` is 5, not 8) this
  way. debugging-007 was verified NOT convertible: with its known spec
  ambiguity excluded from testing (as required), every remaining input
  passes against the unmodified buggy code unchanged, so there's no
  test that actually distinguishes buggy from fixed without either
  resolving the ambiguity or building an unbuilt "doesn't crash" test
  type. Documented in its own metadata; stays manual.
- reasoning-005 narrowed and converted to `exact_match` (verified this
  doesn't reduce the actual reasoning challenge); reasoning-004
  documented as staying manual (needs new eval infrastructure a
  metadata change can't provide).
- Built `backend/app/evaluation/required_facts.py` - zero-cost
  deterministic presence checking, not an LLM judge - and classified
  all 13 summarization tasks explicitly: 6 auto-gradeable, 7 manual
  with a documented reason each, including two hard-flagged tasks
  (009/012) excluded specifically because presence-checking can't
  verify correct attribution, which is the whole point of those tests.
- Consolidated export/rescore tooling into one pass
  (`export_original_run_extras.py` + `apply_remaining_grading_results.py`
  for the no-new-call tasks; `run_groq_revision_batch.py` +
  `apply_revision_batch_results.py` for the 9 tasks needing an actual
  new call) instead of scattering it across separate one-off scripts.
- Registered `groq-qwen3.8-27b` as the proposed third Groq model
  (Phase 4) - different vendor/lineage from gpt-oss, reuses
  GroqProvider, zero new code. No call made, per Phase 4's explicit
  stop condition.

Phase 3 (recompute the analysis) and Phase 5 (V3 readiness with 3
models) are both still blocked on running the above on the user's
machine - nothing in this pass could reach Groq's API from this
sandbox.

## 2026-09-23 — V2.6 data-application phase: tooling fixes, coverage/analysis reporting, Qwen re-check

Still no new API calls reachable from this sandbox - Phase A (export)
and Phase B (revision-batch call) both remain the user's local machine
to run. This pass fixed and extended the tooling those two phases feed
into, ahead of handing back exact commands:

- Fixed a real bug in `apply_revision_batch_results.py`: it only wrote
  `evaluation_status`/`evaluation_detail` onto the existing debugging/
  reasoning-005 records, leaving `latency_ms`, token counts, cost, and
  `error_message` at their stale pre-revision-prompt values. Now every
  field the new call actually measured is replaced, including on a
  failed call, and debugging-007 (which stays ungraded) still gets its
  new metrics recorded.
- Added `scripts/evaluation_coverage_report.py` (Phase C): a per-task,
  three-way split - automatically graded / manual-only / ungraded -
  computed from `evaluation_status`, not the task's declared
  `evaluation_type` (so it correctly counts sandbox- and
  required-facts-graded tasks that keep `evaluation_type="manual"` by
  design). Run against the CURRENT (pre-Phase-A/B) dataset: 75/104
  automatically graded (72.1%), 25 manual-only, 4 ungraded - the 4 are
  exactly reasoning-001/002/003/005, which is what Phase A/B exist to
  fix. Full breakdown in `experiments/results/evaluation-coverage-
  report.md`.
- Added a Token usage section to `analyze_routing_opportunity.py`
  (Phase D asked for it explicitly; it previously reported latency and
  cost but not tokens).
- Re-checked `groq-qwen3.8-27b`'s model id via web search rather than
  trusting the earlier single-aggregator source: a Groq deprecation
  notice (found via search; console.groq.com itself is still blocked
  from this sandbox) confirms `qwen/qwen3.6-27b` was deprecated in
  favor of `qwen/qwen3.8-27b`, and two independent third-party sources
  now agree on the free-tier limits already recorded in the registry
  (30 RPM / 1,000 RPD / 8K TPM / 200K TPD). Stronger corroboration than
  before, but still not a live call - treated with the same caution as
  every other unverified model id until one succeeds.

No routing-opportunity numbers changed this pass - both reports above
were regenerated against the same pre-Phase-A/B data as before, only
the reporting code changed.

## 2026-09-24 — V2.6 Phase A/B applied for real; the 20b/120b tie broke

The user ran Phase A and B locally, walked through step by step with
checkpoints at every stage rather than run-and-hope. Two real problems
surfaced and got fixed along the way, not glossed over:

- **Phase A** (export + rescore reasoning-001/002/003 and 6
  summarization tasks, no new API calls): ran clean on the first try.
  Coverage moved 75/25/4 -> 84/19/1 (ungraded dropped to just
  reasoning-005, exactly as expected once accounting for it needing a
  new call, not a rescore).
- **Phase B** (18 new Groq calls for debugging-001-008 + reasoning-005,
  free tier, \$0 billed): all 18 calls succeeded on the user's Mac, but
  the grading step crashed - `apply_revision_batch_results.py` needs
  `unshare` (Linux/util-linux), which doesn't exist on macOS. Fixed
  narrowly: added the missing `is_sandbox_available()` upfront check
  (its sibling scripts already had it), documented the platform gap in
  `FAILURES_AND_LESSONS.md`, and ran the actual grading in this cloud
  sandbox (confirmed Linux, confirmed `unshare` works) against the
  response data the user had already collected and pushed - no
  macOS fallback built, no new API calls needed, no scope creep.
- Coverage after Phase B: **92/12/0, 88.5% automated** (0 ungraded -
  every automated-evaluation_type task now has real ground truth).

**Recomputing the routing-opportunity analysis surfaced a second real
bug**: `analyze_routing_opportunity.py` hardcoded "these are equal"
when reporting always-20b vs always-120b accuracy - true by coincidence
at 68/75 in the old partial-coverage dataset, but with the fuller
92-task graded set, only_a=3 and only_b=5 are NOT equal. The script
would have kept asserting a tie was true after it stopped being true.
Fixed to check before asserting either way.

**The real finding, once coverage went from 72% to 88.5%: the tie
broke.** always-20b 81/92 (88.0%), always-120b 83/92 (90.2%) - 120b is
now the better unconditional default by 2.2 points, not equal to 20b.
Oracle ceiling: 86/92 (93.5%), 3.3 points above 120b alone (down from
the old finding's "4.0 points above either" - the ceiling itself also
moved once summarization entered the picture, where 120b's edge is
largest: 83.3% vs 50.0% on the 6 auto-gradeable summarization tasks).
120b still costs 1.86x nominal tokens and 1.45x latency for that gain.

**Lesson**: the 2026-09-23 "tie" finding was real in the data available
at the time, but was never a structural fact about the model pair - it
was an artifact of only 72% evaluation coverage. Closing the coverage
gap changed the finding itself, not just its confidence interval. A
routing-opportunity conclusion drawn on a partial graded set should be
labeled provisional, not just "current," until coverage is closer to
complete.

Also updated `backend/tests/test_learned_dataset.py`'s row-count
regression test with real numbers now that reasoning-001/002/003/005
have actual scores: rows 56 -> 59, `no_correct_candidate` 5 -> 2
(math-013, pre-existing, and reasoning-003, which both Groq models
genuinely get wrong). `manual_eval_type` stays 43 - debugging and
summarization tasks keep `evaluation_type="manual"` by design even
once graded (the sandbox/required-facts graders are deliberately not
wired into `EvaluationType`), so Phase A/B enriches evaluation-coverage
reporting without changing V3's training set size.

Still not done: Phase 4 (third-model call, `groq-qwen3.8-27b`, still
needs explicit approval) and Phase 5 (V3 readiness with 3 models,
blocked on Phase 4). V3 itself remains paused - nothing in this pass
retrained it.
