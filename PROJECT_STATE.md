# Project state

Read this before starting any non-trivial change. Keep it concise and
current — update it whenever the stage, objective, or completed work
changes. Full detail belongs in `docs/case-study/`, not here.

## Current stage

V2 — validation, confidence, and escalation. Complete.

## Current objective

None in progress. Before V3 (learned routing), the highest-value step is
still what V1 and V2 both deferred: running real experiments against a
real provider. Every routing rule and every V2 result is still
mock-provider evidence only.

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

## Not implemented (by design, at this stage)

Learned routing (V3), production analytics/observability polish (V4).
No real experiment has been run against a real (non-mock) provider yet —
every V2 result is genuine but mock-only, stated as such throughout.

## Next objective

Run real experiments against at least one real provider (requires an API
key and awareness of cost before running) and record genuine results.
That data should inform whether V1/V2's rules and validators hold up —
and specifically whether the fast/accurate split and the escalation
pattern observed here are real properties of model capability or
artifacts of how MockProvider is built — before V3 (learned routing) is
designed.
