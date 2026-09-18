# benchmarks/

Benchmark task definitions and datasets used to evaluate model and routing
performance.

This is empty during project bootstrap. It is populated in **V0**, when
benchmarking begins, with:

- `tasks/` — individual benchmark task definitions (prompt, expected
  properties, difficulty/category metadata).
- `schemas/` — JSON schema definitions describing the structure of a task
  and of a recorded result, so tasks and results stay consistent as the
  benchmark set grows.

No task data or schemas exist yet — see `PROJECT_STATE.md` at the
repository root for current status.
