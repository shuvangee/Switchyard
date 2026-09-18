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
