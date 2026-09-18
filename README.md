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

V1 complete: Switchyard now routes. Submit a request in the Playground (or
via `POST /route`) and it's analyzed (category, difficulty, structured-
output requirement — transparent heuristics, not a validated classifier),
routed by an explicit, ordered set of rules, executed against the selected
model, and logged in full — request, routing rationale, response, latency,
tokens, cost. Every current rule is derived from V0's mock-provider
baseline (`experiments/results/v0-mock-baseline.json`) and says so in its
rationale; no real (non-mock) provider has been measured yet, so treat the
rules as an evidenced starting point, not a validated finding. See
`PROJECT_STATE.md` for what's completed and what's next, and
`docs/case-study/` — especially `DECISIONS.md` and
`FAILURES_AND_LESSONS.md` — for the reasoning and the real routing
limitations found during verification.

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

Visit `http://localhost:8000/health` or `http://localhost:8000/docs`.
Benchmark tasks and the model registry are synced into a local SQLite
database (`backend/switchyard.db`) automatically on startup.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`. Requires the backend running at the URL in
`NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000`).

### Running an experiment

With both servers running, open `http://localhost:3000/experiments`,
select one or more benchmark tasks and models, and start a run — or via
the API directly:

```bash
curl -X POST http://localhost:8000/experiments \
  -H "Content-Type: application/json" \
  -d '{"task_ids": ["math-001"], "model_config_ids": ["mock-fast-v1", "mock-accurate-v1"]}'
```

### Routing a request

Open `http://localhost:3000/playground`, or via the API directly:

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 17 * 6?"}'
```

The response includes the request analysis, the routing decision (model,
provider, rationale), and the execution result. `GET /requests` lists
every routed request; `backend/app/routing/rules.py` is the one place
routing rules are configured.

### Adding a benchmark task

Add a JSON file to `benchmarks/tasks/` (filename must match the task's
`id`) and restart the backend — see `benchmarks/README.md` for the schema.

### Environment variables

Copy `.env.example` to `.env` (backend) and/or `frontend/.env.local` as
needed. No API keys are required for local development — the mock
provider (three models: fast/cheap, slow/accurate, flaky) runs without any
paid API usage. Setting `OPENAI_API_KEY` enables the real OpenAI adapter
in the model registry; without it, that model is listed but disabled.

## Contributing / working on this repo

Read `CLAUDE.md` for engineering principles and documentation
requirements, and `PROJECT_STATE.md` before starting any non-trivial
change.
