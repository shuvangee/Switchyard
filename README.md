# Switchyard

Switchyard is an adaptive multi-model AI routing system. Instead of
sending every request to the same model, it analyzes each task and decides
which available model should handle it, based on factors such as task
type, task difficulty, expected answer quality, model capability,
inference cost, response latency, reliability, context requirements, and
historical performance.

## Research question

Can an intelligent routing system significantly reduce AI inference cost
and latency without meaningfully reducing answer quality?

This is a research case study first and a product second: every claim it
eventually makes about cost or latency savings is backed by a measured
experiment, not an assumption. See `docs/case-study/` for the running
record of decisions, experiments, and results.

## Development stages

The project is built incrementally rather than as a single large system:

| Version | Scope |
|---|---|
| V0 | Model performance benchmarking |
| V1 | Rule-based multi-model routing |
| V2 | Evaluation, confidence, fallback, and escalation |
| V3 | Learned routing |
| V4 | Production-style analytics, observability, and final case study |

## Current status

Project bootstrap. The repository structure, tooling, and documentation
conventions are in place; no routing, benchmarking, provider integration,
or evaluation logic exists yet. See `PROJECT_STATE.md` for the current
objective and what's been completed.

## Architecture direction

- **`frontend/`** — Next.js / React / TypeScript. UI only.
- **`backend/`** — Python / FastAPI. Owns routing, provider adapters,
  evaluation, persistence, and experiment execution, organized by
  responsibility (see `docs/architecture/overview.md`).
- **`benchmarks/`** — versioned benchmark task definitions and schemas.
- **`experiments/`** — reproducible experiment configuration and results.
- **`docs/`** — architecture notes and the ongoing case study.
- **`scripts/`** — one-off developer scripts.

AI provider access goes through an adapter interface (`backend/app/providers/`)
so application logic is never coupled to a specific vendor SDK, and a mock
provider keeps local development free. Persistence uses SQLite, structured
so a later migration is possible without a rewrite. No Kubernetes,
microservices, message queues, or other heavy infrastructure — those are
only introduced if a later version genuinely requires them.

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/health`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`.

### Environment variables

Copy `.env.example` to `.env` (backend) and/or `frontend/.env.local` as
needed. No API keys are required for local development — mock providers
(added in V0) run without paid API usage.

## Contributing / working on this repo

Read `CLAUDE.md` for engineering principles and documentation
requirements, and `PROJECT_STATE.md` before starting any non-trivial
change.
