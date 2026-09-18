# Architecture overview

Status: V0 (model performance lab). This describes what exists right now,
not the eventual full system — that grows incrementally alongside
`PROJECT_STATE.md`.

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

- `api/` — HTTP route definitions (`benchmarks.py`, `model_configs.py`,
  `experiments.py`), plus request/response schemas kept separate from the
  ORM layer (`schemas.py`).
- `core/` — configuration (`config.py`) and cross-cutting helpers
  (`time.py`).
- `models/` — `BenchmarkTaskORM`/`BenchmarkTaskSchema`, `ModelConfigORM`,
  `ExperimentRunORM`/`ModelExecutionORM`, and the shared enums
  (`TaskCategory`, `TaskDifficulty`, `EvaluationType`, `ExecutionStatus`,
  `EvaluationStatus`, `RunStatus`).
- `providers/` — the `Provider` interface, `MockProvider` (three
  deterministic profiles), `OpenAIProvider` (real, disabled without a
  key), pure cost estimation (`pricing.py`), and the single model registry
  (`registry.py`) that builds `ModelConfig` objects and syncs them into
  the `model_configs` table.
- `evaluation/` — `exact_match`, `classification_label`, `valid_json`, and
  `manual` strategies behind one `evaluate()` dispatcher.
- `experiments/` — `loader.py` (validates benchmark task files and syncs
  them into the DB) and `runner.py` (`run_experiment()`/`execute_single()`).
- `db/` — SQLAlchemy engine/session (`session.py`), the declarative base
  (`base.py`), and table creation (`init_db.py`).
- `routing/` — still an empty stub. V0 deliberately measures raw model
  performance with no routing decisions yet; this is where a rule-based
  strategy (V1) and a learned strategy (V3) will live behind a shared
  interface, swappable without touching call sites.

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
