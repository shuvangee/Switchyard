# Project state

Read this before starting any non-trivial change. Keep it concise and
current — update it whenever the stage, objective, or completed work
changes. Full detail belongs in `docs/case-study/`, not here.

## Current stage

V0 — model performance lab. Complete.

## Current objective

None in progress. Awaiting direction on V1 (rule-based multi-model
routing) — which should start only after real experiments have actually
been run against real providers and looked at, not immediately.

## Completed

**Bootstrap:** repository structure, engineering docs (`CLAUDE.md`,
this file), case-study skeleton, root `README.md`/`.env.example`/
`.gitignore`, minimal FastAPI health check, minimal Next.js status page.

**V0:**
- Persistence: SQLAlchemy ORM for `benchmark_tasks`, `model_configs`,
  `experiment_runs`, `model_executions` (`backend/app/models/`, `db/`).
- Providers: `Provider` interface, `MockProvider` (three deterministic
  profiles — fast/cheap/basic-skill, slow/pricier/capable-skill,
  flaky/error-prone), `OpenAIProvider` (real, disabled without
  `OPENAI_API_KEY`, never called live in this environment), cost
  estimation, and a single centralized model registry
  (`backend/app/providers/`).
- Evaluation: `exact_match`, `classification_label`, `valid_json`, and
  `manual` strategies distinguishing "not evaluated" from "evaluated and
  failed" (`backend/app/evaluation/`).
- Benchmark tasks: 12 sample tasks across all 8 categories, authored as
  JSON files in `benchmarks/tasks/`, validated and synced into the DB at
  startup (`backend/app/experiments/loader.py`).
- Experiment runner: executes every (task, model) pair, continues past
  individual provider failures, records latency/tokens/cost/evaluation
  (`backend/app/experiments/runner.py`).
- API: `GET/POST /benchmarks`, `GET /models`, `GET/POST /experiments`,
  `GET /experiments/{id}` (`backend/app/api/`).
- Frontend: Overview (live counts + recent runs), Benchmarks (filterable
  list + detail), Experiments (start-run form + run detail with every
  execution's task/model/provider/status/latency/tokens/cost/evaluation/
  response/error).
- Tests: 68 backend tests (pytest) covering the loader, providers,
  pricing, evaluation, the runner, and every API endpoint; frontend
  typechecks and builds cleanly with the backend not running.
- Verified end to end against the real (non-test) server: a 36-execution
  run (12 tasks x 3 mock models) correctly showed different cost/latency/
  correctness profiles per model — see `docs/case-study/DEVELOPMENT_LOG.md`.

## Not implemented (by design, at this stage)

Routing of any kind (rule-based, learned), confidence/escalation,
production analytics/observability. No real experiment has been run
against a real (non-mock) provider yet — `METRICS.md`/`EXPERIMENTS.md`
stay empty until that happens.

## Next objective

Run real experiments against at least one real provider (requires an
API key and awareness of cost before running), record genuine results in
`docs/case-study/EXPERIMENTS.md`/`METRICS.md`, then design V1 (rule-based
multi-model routing) informed by what those results actually show.
