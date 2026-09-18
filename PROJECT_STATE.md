# Project state

Read this before starting any non-trivial change. Keep it concise and
current — update it whenever the stage, objective, or completed work
changes. Full detail belongs in `docs/case-study/`, not here.

## Current stage

V1 — rule-based multi-model routing. Complete.

## Current objective

None in progress. Before V2 (evaluation, confidence, fallback,
escalation), the highest-value next step is running real experiments
against a real provider — every routing rule in V1 is still mock-provider
evidence only.

## Completed

**Bootstrap + V0** (full detail in `docs/case-study/DEVELOPMENT_LOG.md`):
repository structure, engineering docs, persistence, provider abstraction
(mock + disabled-without-key OpenAI adapter), evaluation strategies,
benchmark task set, experiment runner, benchmarks/models/experiments API
+ frontend.

**V1:**
- `scripts/run_v0_baseline.py` + `experiments/results/v0-mock-baseline.json`
  — the first real content in `experiments/`; the evidence V1's rules are
  based on (mock provider only, stated explicitly).
- Request analyzer (`backend/app/routing/analyzer.py`): heuristic
  category/difficulty/structured-output/token-estimate from a raw prompt,
  explicitly not claiming to be a validated classifier.
- Routing rules (`backend/app/routing/rules.py`): 3 rules, each citing the
  specific V0 baseline numbers behind it — easy deterministic tasks
  (extraction/classification/math/structured_output) → `mock-fast-v1`;
  medium/hard → `mock-accurate-v1`; the 4 never-scored manual-eval
  categories → `mock-accurate-v1` as a conservative default.
  `mock-flaky-v1` is never a routing target.
- Router (`backend/app/routing/router.py`): first-match-wins, degrades
  gracefully if a rule's target model is disabled.
- Request logging (`RequestLogORM` + `backend/app/routing/service.py`):
  every routed request's analysis, decision, and execution result
  persisted as one row, regardless of outcome.
- API: `POST /route`, `GET /requests`, `GET /requests/{id}`; `GET /models`
  now includes a live-computed (never fixed) V0 performance summary per
  model.
- Frontend: Playground (submit a request, see the full analysis/decision/
  response/metadata), Request History (list + detail), Models (full
  table with live performance).
- Tests: 104 backend tests (pytest) — 36 new for the analyzer, rules,
  router, routing service, and routing API endpoints; frontend typechecks
  and builds cleanly with the backend not running.
- Verified end to end against a live server: 12 representative requests
  across all 8 categories through `/route`, confirmed on both the API and
  the rendered pages. Verification surfaced two real, documented
  limitations rather than being smoothed over — see
  `docs/case-study/FAILURES_AND_LESSONS.md`:
  1. The word-count difficulty heuristic misroutes "What is -8 + 15?"
     (estimated easy → wrong answer from `mock-fast-v1`); an identical
     problem rephrased with more words is estimated medium and answered
     correctly, for the wrong reason (word count, not actual difficulty).
  2. A correctly-routed classification request got a generic fallback
     response because `MockProvider`'s classification heuristic only
     recognizes the exact phrasing used in the curated V0 benchmark
     tasks, not open-ended Playground input.

## Not implemented (by design, at this stage)

Confidence estimation, escalation, learned routing, production analytics/
observability. No real experiment has been run against a real (non-mock)
provider yet — `METRICS.md`/`EXPERIMENTS.md` stay empty of real-model
numbers until that happens; V1's routing rules are explicitly labeled as
mock-provider evidence throughout, not a validated finding.

## Next objective

Run real experiments against at least one real provider (requires an API
key and awareness of cost before running) and record genuine results.
That data should inform whether V1's rules hold up, before V2 (confidence
scoring and escalation — which the documented misrouting case above is a
direct, concrete argument for) is designed.
