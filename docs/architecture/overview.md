# Architecture overview

Status: V2 (validation, confidence, and escalation on top of V1's
rule-based routing). This describes what exists right now, not the
eventual full system — that grows incrementally alongside
`PROJECT_STATE.md`.

## Core flow (V2)

```
raw prompt
  -> app/routing/analyzer.py    (category, difficulty, structured-output
                                  flag, estimated tokens — transparent
                                  heuristics, not a real classifier)
  -> app/routing/rules.py       (DEFAULT_RULES: ordered, evidence-cited)
  -> app/routing/router.py      (decide_route: first matching rule whose
                                  target model is enabled; also computes
                                  confidence and can preemptively escalate
                                  the initial pick when it's LOW)
  -> app/routing/service.py     (handle_routed_request: the retry loop —
                                  calls the chosen Provider, validates the
                                  response, escalates to
                                  ESCALATION_TARGETS on a ProviderError or
                                  a FAILED validation, bounded by
                                  MAX_ATTEMPTS, records a TraceEvent at
                                  every step)
       |-> app/evaluation/validation.py  (content-level check inferred
       |                                  from the request itself — no
       |                                  pre-authored expected_output
       |                                  exists for freeform requests)
       |-> app/routing/trace.py          (TraceEvent: system-level facts
                                           only, never model reasoning)
  -> RequestLogORM               (request_logs table — one row per
                                   request: analysis + decision +
                                   escalation history + final execution +
                                   full trace_events)
```

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
  `experiments.py`, `routing.py`, `analytics.py`), plus request/response
  schemas kept separate from the ORM layer (`schemas.py`).
- `core/` — configuration (`config.py`) and cross-cutting helpers
  (`time.py`).
- `models/` — `BenchmarkTaskORM`/`BenchmarkTaskSchema`, `ModelConfigORM`,
  `ExperimentRunORM`/`ModelExecutionORM`, `RequestLogORM`, and the shared
  enums (`TaskCategory`, `TaskDifficulty`, `EvaluationType`,
  `ExecutionStatus`, `EvaluationStatus`, `RunStatus`, `ValidationStatus`,
  `ConfidenceLevel`).
- `providers/` — the `Provider` interface, `MockProvider` (three
  deterministic profiles), `OpenAIProvider` (real, disabled without a
  key), pure cost estimation (`pricing.py`), and the single model registry
  (`registry.py`) that builds `ModelConfig` objects and syncs them into
  the `model_configs` table.
- `evaluation/` — `strategies.py` (`exact_match`, `classification_label`,
  `valid_json`, `manual` — grading a benchmark task against its
  pre-authored `expected_output`) and `validation.py` (`validate_response()`
  — checking a *live* routed response against whatever can be inferred
  from the request itself; no expected_output exists for freeform input,
  so this is a deliberately separate module and enum — see
  `docs/case-study/DECISIONS.md`).
- `experiments/` — `loader.py` (validates benchmark task files and syncs
  them into the DB) and `runner.py` (`run_experiment()`/`execute_single()`).
- `db/` — SQLAlchemy engine/session (`session.py`), the declarative base
  (`base.py`), and table creation (`init_db.py`).
- `routing/` — `analyzer.py` (heuristic `RequestAnalysis`), `rules.py`
  (`DEFAULT_RULES`, each citing specific V0 baseline evidence, plus
  `ESCALATION_TARGETS`), `router.py` (`decide_route()`, pure and DB-free —
  also computes confidence and applies the low-confidence override),
  `trace.py` (`TraceEvent`, system-facts-only), and `service.py`
  (`handle_routed_request()`, the bounded validate/escalate retry loop
  that persists a `RequestLogORM`). A learned strategy (V3) will live
  alongside `rules.py` behind the same `decide_route()`-shaped interface,
  swappable without touching `service.py`.

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
