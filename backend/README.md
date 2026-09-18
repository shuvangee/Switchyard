# Switchyard backend

FastAPI service that will eventually host routing, provider adapters,
evaluation, and experiment execution. During bootstrap it only exposes a
health check so the environment can be verified end to end.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/health` or `http://localhost:8000/docs`.

## Test

```bash
pytest
```

## Layout

- `app/api/` — HTTP route definitions.
- `app/core/` — configuration and cross-cutting concerns.
- `app/models/` — data models / ORM schema.
- `app/providers/` — AI provider adapters (mock, OpenAI, Anthropic, Google, ...).
- `app/routing/` — routing strategies (rule-based, learned, ...).
- `app/evaluation/` — response scoring and quality evaluation.
- `app/experiments/` — experiment execution and orchestration.
- `app/db/` — persistence layer (SQLite).

Most of these packages currently contain only a docstring describing their
future purpose — see `PROJECT_STATE.md` at the repository root for what is
actually implemented right now.
