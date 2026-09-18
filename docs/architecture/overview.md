# Architecture overview

Status: bootstrap. This describes what exists right now, not the eventual
full system — that grows incrementally alongside `PROJECT_STATE.md`.

## Repository shape

Switchyard is split into independently runnable pieces so the AI/engine
work (Python) never gets entangled with the UI (TypeScript):

- `frontend/` — Next.js/React/TypeScript. UI only; no business logic.
- `backend/` — FastAPI/Python. Owns routing, provider adapters, evaluation,
  persistence, and experiment execution.
- `benchmarks/` — versioned task definitions used as evaluation input.
- `experiments/` — recorded configuration/results from experiment runs.
- `docs/` — architecture notes and the running case study.
- `scripts/` — one-off developer scripts, not application code.

The frontend and backend communicate over HTTP; nothing else currently
links them together.

## Backend internal structure

`backend/app/` is organized by responsibility rather than by feature, since
the responsibilities are stable even as features are added:

- `api/` — HTTP route definitions only (thin controllers).
- `core/` — configuration and cross-cutting concerns (settings, logging).
- `models/` — data models / ORM schema.
- `providers/` — one adapter per AI provider (and a mock provider) behind a
  shared interface, so routing/evaluation code is never coupled to a
  specific vendor SDK.
- `routing/` — routing strategies behind a shared interface, so a
  rule-based strategy (V1) and a learned strategy (V3) can be swapped and
  compared without touching call sites.
- `evaluation/` — scoring of model responses, independent of which
  provider or routing strategy produced them.
- `experiments/` — orchestrates a benchmark run against a chosen provider
  set and routing strategy, and records the result.
- `db/` — persistence, SQLite initially.

Only `api/health.py`, `core/config.py`, and `main.py` currently contain
real logic. Everything else is a stub with a docstring describing its
future responsibility — see `PROJECT_STATE.md` for what is actually
implemented.

## Why these choices

- **SQLite over a client/server database initially**: the project runs on
  a student budget with a single developer; SQLite has zero operational
  cost and the persistence layer is kept thin enough to migrate later if a
  real need appears (concurrent writers, larger datasets).
- **Provider adapter interface from the start**: even though no real
  provider integration exists yet, routing and evaluation logic must never
  import a vendor SDK directly — this is what makes a mock provider (for
  free local development) and multi-provider comparison (the actual
  research question) possible without rewrites later.
- **No queues, no Kubernetes, no microservices**: request volume is a
  handful of benchmark calls at a time, not production traffic. A single
  FastAPI process is sufficient until a version genuinely requires more.
- **Next.js App Router for the frontend**: a small, standard choice with
  no meaningful project-specific trade-off at this stage.
