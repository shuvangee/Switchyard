# Project state

Read this before starting any non-trivial change. Keep it concise and
current — update it whenever the stage, objective, or completed work
changes. Full detail belongs in `docs/case-study/`, not here.

## Current stage

V2 — validation, confidence, and escalation. Complete.

## Current objective

None in progress. Switchyard's first real-provider experiment (Gemini)
is now done — see Completed below. V3 (learned routing) is still not
started: the 2026-09-19 data-readiness review found the existing dataset
insufficient, and this one 12-task real-provider run, while genuine, does
not change that conclusion by itself (see `docs/case-study/EXPERIMENTS.md`).

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
  full breakdown — not fixed here, since fixing it was out of scope for
  this run (see that entry for why fixing it isn't a small edit).

## Not implemented (by design, at this stage)

Learned routing (V3), production analytics/observability polish (V4). One
real-provider run now exists (12 tasks, Gemini 3.6 Flash) but is a single
run against one model — not enough by itself to redo the V3
data-readiness verdict.

## Next objective

Two candidates, not yet prioritized against each other:
1. Fix V0's evaluation strategies to tolerate a real model's response
   style (strip markdown fences, use substring/semantic matching instead
   of whole-string equality) — otherwise every future real-provider
   number this project reports understates real quality.
2. Run more real-provider experiments (more tasks, repeated trials, the
   4 never-graded categories, possibly a second real provider) to build
   toward enough data for the V3 data-readiness bar.
