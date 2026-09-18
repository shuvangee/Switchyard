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
