# Project state

Read this before starting any non-trivial change. Keep it concise and
current — update it whenever the stage, objective, or completed work
changes. Full detail belongs in `docs/case-study/`, not here.

## Current stage

Project bootstrap / pre-V0.

## Current objective

Establish architecture, documentation, tooling, and project conventions.

## Completed

- Repository structure created: `frontend/`, `backend/`, `benchmarks/`,
  `experiments/`, `docs/` (`architecture/`, `case-study/`), `scripts/`.
- Backend: minimal FastAPI app (`backend/app/main.py`) with a `/health`
  endpoint, environment-based configuration (`backend/app/core/config.py`),
  and stub packages (with docstrings only) for `models/`, `providers/`,
  `routing/`, `evaluation/`, `experiments/`, `db/`. Test suite (`pytest`)
  covering the health endpoint. `requirements.txt` / `requirements-dev.txt`.
- Frontend: minimal Next.js (App Router) + React + TypeScript app with a
  single status page (project name, research question, version roadmap,
  current stage) — no dashboards or live data yet.
- `CLAUDE.md` — permanent engineering instructions.
- `PROJECT_STATE.md` — this file.
- `docs/architecture/overview.md` — current architecture and reasoning.
- `docs/case-study/` — `PROJECT_STORY.md`, `DEVELOPMENT_LOG.md` (first
  real entry for bootstrap), `DECISIONS.md` (three real entries for
  bootstrap decisions), `EXPERIMENTS.md`, `FAILURES_AND_LESSONS.md`,
  `METRICS.md`, `WEBSITE_CASE_STUDY.md` (structure/headings only, no
  fabricated content).
- Root `README.md`, `.env.example`, `.gitignore` (Python + Node/Next.js).
- Verified: backend starts (`uvicorn`) and `pytest` passes; frontend
  builds (`npm run build`) and typechecks.

## Not implemented (by design, at this stage)

Routing, benchmark execution, real or mock model providers, dashboards,
experiment execution, and learned ML — all intentionally deferred to V0
and later.

## Next objective

Design and implement V0: model performance benchmarking (benchmark task
schema, a small initial task set, a mock provider, and a script/endpoint
to run tasks against models and record raw quality/cost/latency results).
