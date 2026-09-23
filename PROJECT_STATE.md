# Project state

Read this before starting any non-trivial change. Keep it concise and
current — update it whenever the stage, objective, or completed work
changes. Full detail belongs in `docs/case-study/`, not here.

## Current stage

V3 — learned routing. Retrained on real data twice: first on 24 rows
(2026-09-22), then on 56 rows after the Groq gpt-oss-20b/120b run
(2026-09-23). **Result both times: it loses to a trivial single-model
baseline.** Not recommended for real traffic — `v2` remains the default
router. See `docs/case-study/EXPERIMENTS.md` (2026-09-22 and 2026-09-23
entries) for the full analysis, and `FAILURES_AND_LESSONS.md`
(2026-09-23) for two real bugs in the *evaluation methodology* found and
fixed while re-checking the second retrain's initial (misleadingly
positive) numbers — this remains an honest negative result, not a bug in
the router itself to be quietly fixed.

## Current objective

1. Data collection more than doubled the training set (24 → 56 rows) and
   changed which model dominates (`mock-fast-v1` → `groq-gpt-oss-20b`),
   but did not change the underlying finding: a trivial "always pick one
   model" policy still beats the learned router. The 4 manual-eval
   categories (coding, debugging, reasoning-manual, summarization) still
   contribute zero training rows — that's the next real lever, not
   another retrain on the same auto-graded categories.
2. Nothing about V3's pipeline itself needs more work right now — it's
   built, tested, and wired into the router-selection mechanism
   (`router_version="learned-v1"` in `POST /route`). The evaluation
   methodology in `train.py` was hardened this pass (dynamic baseline
   model selection, every candidate model checked as its own trivial
   baseline, explicit `learned_v1_beats_every_single_model_baseline`
   flag) specifically so a future retrain's result can't look like a win
   without actually being one.
3. This sandbox's network policy blocks `groq.com` outright — any future
   real-provider run against Groq needs to happen from outside this
   environment (see `FAILURES_AND_LESSONS.md`, 2026-09-23).

## Completed

**Bootstrap + V0 + V1:** see `docs/case-study/DEVELOPMENT_LOG.md` for
full detail — repository structure, engineering docs, persistence,
provider abstraction, evaluation strategies, benchmark task set,
experiment runner, benchmarks/models/experiments API + frontend, the
request analyzer, rule-based router, request logging, and the
Playground/Request History/Models frontend.

**V2:**
- Validation (`backend/app/evaluation/validation.py`): content-level
  checks for a *live* routed response (no pre-authored expected_output
  exists) — math (independently recomputed), classification (checked
  against an explicit label list when the prompt has one),
  structured_output (valid JSON), extraction (well-formed email format).
  Everything else — and any of those four without an extractable
  signal — is honestly `NOT_VALIDATED`, never guessed.
- Confidence (`backend/app/routing/router.py:estimate_confidence`): a
  heuristic HIGH/MEDIUM/LOW label, explicitly not calibrated. LOW
  (no category signal found at all) can preemptively escalate the initial
  model choice.
- Escalation (`ESCALATION_TARGETS`, `MAX_ATTEMPTS=2` in
  `backend/app/routing/service.py`): a `ProviderError` or a validation
  `FAILED` outcome retries with a stronger model, bounded so a chain of
  failures can never loop.
- Request trace (`backend/app/routing/trace.py`,
  `RequestLogORM.trace_events`): an ordered, timestamped list of
  system-level events (received/analyzed/routed/model_completed/
  provider_error/validation/escalating/returned) — never model reasoning.
- API: `GET /analytics` (live-computed: request count, initial/final
  model distributions, escalation rate, provider errors, avg latency,
  total cost, validation pass/fail/not-validated); `POST /route` and
  `GET /requests`/`GET /requests/{id}` now expose confidence, escalation
  history, validation status, and the full trace.
- Frontend: `RequestTrace` (distributed-tracing-style timeline) on the
  Playground and request detail pages; an Analytics page; escalation/
  validation columns on Request History; an escalation-rate stat on
  Overview.
- Tests: 130 backend tests (pytest) — 17 new for validation, confidence,
  escalation, and the retry-limit guarantee (forced via monkeypatching
  since the real mock-accurate-v1 tier doesn't naturally fail twice);
  frontend typechecks and builds cleanly with the backend not running.
- **Verified the actual fix, not just the mechanism**, on the real
  (unmocked) pipeline: the literal V1 failure prompt
  (`"What is -8 + 15?"`) now escalates from `mock-fast-v1` (wrong, `23`)
  to `mock-accurate-v1` (correct, `7`), attempt_count=2, ~650ms extra
  latency, one extra paid-tier call. **Also verified, and reported
  honestly, that V2 does NOT fix the V1 classification-phrasing
  failure** — validation and the mock provider share the same
  `"one of:"` phrasing dependency, so no `FAILED` signal is ever produced
  to escalate on. See `docs/case-study/EXPERIMENTS.md` for both, plus a
  third finding (classification validation checks label *membership*,
  not semantic correctness) and a documented, unresolved gap (escalated
  requests only record the final attempt's latency/cost, not the sum
  across attempts — see `docs/case-study/DECISIONS.md`).

**First real-provider experiment (2026-09-20):**
- Added `GeminiProvider` (`backend/app/providers/gemini_provider.py`) and
  `scripts/run_gemini_baseline.py`, which runs the 12 benchmark tasks
  against exactly one real model_config_id (not mixed with mock data),
  with retry-with-backoff on rate limits.
- Getting a working model id took three attempts: `gemini-2.0-flash` and
  `gemini-2.5-flash` both 404'd (retired for this key/account); Google's
  own error message named `gemini-3.6-flash` as the replacement, which is
  what's registered and was actually run. See
  `docs/case-study/FAILURES_AND_LESSONS.md`.
- Result: **12/12 tasks succeeded** (after 2 rate-limit retries + 1 manual
  retry on a transient 503), real cost **$0.00157**, real tokens (334 in /
  353 out), real latency (~3.7s avg — 5-70x slower than any mock profile).
  Full data: `experiments/results/gemini-3.6-flash-baseline.json`.
- **The important finding is not about Gemini — it's about V0's
  evaluators.** Manually reading all 12 responses: all 8
  deterministically-scored tasks got a substantively correct answer, but
  the automated evaluator (`evaluate_exact_match`/`evaluate_valid_json`)
  only marked 3/8 `correct`. The other 5 are false negatives — a real
  model answers in full sentences and wraps JSON in markdown fences;
  `exact_match` requires the whole normalized string to match, and
  `evaluate_valid_json` calls `json.loads()` on the raw response with no
  fence-stripping. Both were implicitly written against MockProvider's
  terse, unwrapped output style. See `FAILURES_AND_LESSONS.md` for the
  full breakdown.

**Evaluator fix (2026-09-20):** `evaluate_exact_match` now falls back to a
word-bounded token match when whole-string equality fails;
`evaluate_valid_json` now retries once with a markdown code fence
stripped. Verified with no new API calls — `scripts/rescore_evaluator_fix.py`
re-scored all 48 existing rows (36 mock, regenerated deterministically via
`MockProvider`; 12 Gemini, using the real saved raw response text): exactly
the 5 diagnosed rows changed, all `incorrect` → `correct`, zero
regressions. Gemini's deterministically-scored tasks now read 8/8 correct.
140 backend tests pass (up from 136). Full detail in
`FAILURES_AND_LESSONS.md` (2026-09-20 entry, updated in place).

## V3 — learned routing (2026-09-22)

Built the full pipeline: `backend/app/routing/learned/{dataset,features,train}.py`
(dataset construction, feature encoding, leave-one-out evaluation +
baseline comparison + final artifact training) and
`backend/app/routing/learned_router.py` (inference-time strategy,
same `RoutingDecision` shape as V1's rule-based router). Wired into
`routing/service.py`/`api/schemas.py`/`api/routing.py` as a selectable
`router_version` (`"v2"` default, `"learned-v1"` opt-in). 24 real training
rows (mock + the one real Gemini experiment — the 4 manual-eval
categories contribute none, honestly, since there's no ground truth for
them). New dependency: `scikit-learn`/`joblib`. 21 new tests
(167 backend tests total, up from 146).

**Result: learned-v1 loses.** 56.5% leave-one-out accuracy vs.
always-cheapest's 58.3% (at 5.5x lower cost), V1's rules' 75.0%, and
random's 72.9%. Strictly dominated by always-cheapest on both accuracy
and cost. Root cause: not enough data (24 rows, 3 severely imbalanced
classes) — exactly what three prior data-readiness reviews predicted,
now demonstrated with a real trained model rather than argued in the
abstract. Verified this is a data problem, not a pipeline bug, via a
synthetic-data test that recovers ≥90% accuracy on a genuinely learnable
pattern using the identical code path. Full analysis, including a
same-day catch that the Gemini evaluator fix from 2026-09-20 had been
verified but never actually written back to its own results file:
`docs/case-study/EXPERIMENTS.md` and `FAILURES_AND_LESSONS.md`
(2026-09-22 entries).

**Not built in this pass:** a dedicated frontend comparison UI (the
original V3 ask). Substituted with `scripts/report_v3_comparison.py`,
which renders the same real comparison numbers as a markdown table
(`experiments/results/learned-v1-comparison.md`) — building a full page
for a router that isn't recommended for use felt like the wrong
priority; revisit once there's a result worth putting in front of a
reviewer as a working feature, not just a documented finding.

## Not implemented (by design, at this stage)

Production analytics/observability polish (V4) — not started, and V3's
negative result means it shouldn't be, until a learned router actually
has something to show.

## Data-collection plan (in progress)

Collecting enough real data to responsibly revisit the V3 data-readiness
verdict. Explicitly asked whether to skip ahead to V3 anyway (2026-09-20)
and decided against it — see "Not implemented" above.

**Phase 1 — expand the benchmark set (done, 2026-09-20):**
- 12 → 44 tasks (4 new per category, all 8 categories now have 5-6 tasks
  spanning easy/medium/hard, up from 1-2).
- The 4 auto-scored categories (math, extraction, classification,
  structured_output) got real `expected_output` values.
- The 4 manual categories (coding, debugging, reasoning, summarization)
  got a written grading rubric in each task's `metadata.notes` — chosen
  over an LLM-judge specifically so a human (not another model) makes the
  first real quality calls for these categories.
- Mock baseline regenerated against all 44 tasks — free, no real cost.
- **Incident during this phase:** regenerating the mock baseline via
  `scripts/run_v0_baseline.py` also made 44 real, unapproved Gemini calls
  (real cost: $0.0000585) because the script selected models by
  `enabled`, not by provider — an assumption that broke the moment a real
  API key existed. Fixed (now scoped to `provider == "mock"` explicitly)
  and the corrupted results file was restored from git. Full write-up:
  `docs/case-study/FAILURES_AND_LESSONS.md` (2026-09-20).

**Phase 2 — manual grading of the 4 previously-unscored categories
(in progress, 2026-09-21):**
- Generated real Gemini responses for all 20 tasks
  (`scripts/generate_manual_grading_responses.py`) — mock's response to
  these is always its generic templated fallback, not worth grading.
- 18/20 succeeded ($0.004310 real cost); 2 (`reasoning-004`,
  `summarization-001`) still need a response — blocked by Gemini's
  free-tier **daily** quota (20 requests/day/model, not just a per-minute
  limit — see `FAILURES_AND_LESSONS.md`).
- **The 18 collected responses are not gradeable as generated** — most
  are truncated mid-sentence. `gemini-3.6-flash` is a reasoning model;
  invisible thinking tokens counted against the same 512-token cap as the
  visible answer, leaving as little as ~16 tokens for the real response.
  Cap raised to 2048 in `backend/app/providers/gemini_provider.py`; the
  flawed batch is kept at `experiments/results/manual-grading-gemini-3.6-flash.{json,md}`
  as a record but flagged at the top of the `.md` file as not to be
  graded. Needs regenerating once the daily quota allows.
- **2026-09-21 retry:** attempted regeneration again — quota had *not*
  reset despite the calendar date rolling over (exact reset timing still
  unconfirmed). The script also had its own bug: it would have silently
  overwritten the 18 real responses already captured with blank failures.
  Fixed (script now only ever adds successful responses, never erases a
  previously-successful one) and the near-loss was caught via
  `git diff --stat` before committing — full write-up in
  `FAILURES_AND_LESSONS.md`. State unchanged: still 18/20 real (but
  truncated, not gradeable) responses on file.
- **Not yet done:** regenerate all 20 with the fixed 2048-token cap, once
  the daily quota allows, then the user grades each against its
  `metadata.notes` rubric. V3 training itself remains at zero lines of
  code — this is still prerequisite data collection, not V3.

**Phase 3 — re-run real-provider experiments on the expanded set:**
Not started. Needs a cost estimate and approval before any call, same as
the first Gemini run.
