# benchmarks/

Benchmark task definitions used to evaluate model performance (V0) and,
later, routing decisions.

- `tasks/` — one JSON file per benchmark task. This is the source of
  truth: the backend loads every `*.json` file here at startup, validates
  it, and syncs it into the `benchmark_tasks` table (see
  `backend/app/experiments/loader.py`).
- `schemas/task.schema.json` — documents the task file shape. It mirrors
  `backend/app/models/benchmark.py:BenchmarkTaskSchema`, which is what
  actually validates task files at load time.

## Adding a benchmark task

1. Create `benchmarks/tasks/<id>.json`, where `<id>` is a unique string
   and the filename (without `.json`) must equal the task's `id` field.
2. Fill in the required fields — see `schemas/task.schema.json`:
   - `id`, `title`, `category`, `difficulty`, `prompt`, `evaluation_type`
   - `expected_output` — required for `exact_match`/`classification_label`;
     optional for `valid_json` (checked as a key set, not an exact match);
     omit (or `null`) for `manual`.
   - `metadata` — free-form (tags, notes); not used by evaluation logic.
3. Restart the backend (or re-run the test suite) — task files are synced
   into the database at startup, not hot-reloaded while the process runs.

`evaluation_type` determines how a response is graded (see
`backend/app/evaluation/strategies.py`):

| evaluation_type | how it's checked |
|---|---|
| `exact_match` | normalized (trimmed, lowercased) string equality against `expected_output` |
| `classification_label` | same normalized equality, for label-style answers |
| `valid_json` | response must parse as JSON; if `expected_output` is a JSON object, its keys must match the response's keys |
| `manual` | never auto-scored — always recorded as "not evaluated" |

## Current task set

12 sample tasks across all 8 categories (extraction, classification,
summarization, math, reasoning, coding, debugging, structured_output),
spanning easy/medium/hard — enough to exercise every evaluation type and
demonstrate the system end to end. This is a starter set for exercising
the pipeline, not a comprehensive benchmark suite.
