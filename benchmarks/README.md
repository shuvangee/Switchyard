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

104 tasks across all 8 categories (extraction, classification,
summarization, math, reasoning, coding, debugging, structured_output;
13 tasks each), spanning easy/medium/hard. Expanded from the original 12
(2026-09-20, Phase 1 of the post-V2 data-collection plan — see
`PROJECT_STATE.md`) specifically to give the 4 auto-scored categories
(math, extraction, classification, structured_output) enough tasks to
mean something beyond 1-2 examples, and to give the 4 manual categories
(coding, debugging, reasoning, summarization) a written grading rubric in
`metadata.notes` for each task, since those were never graded before.

Expanded again (2026-09-22, ahead of the Groq/Grok benchmark round) from
44 to 104 tasks, deliberately including harder cases per category (marked
`hard` in `metadata.tags`, with a `metadata.hard_reason` explaining why a
fast/cheap model would plausibly get it wrong) so the dataset isn't
dominated by trivially-easy examples. This round also:

- Added `metadata.test_cases` (input → expected output) to every coding
  task, including the original 5, so a future test-execution grader has
  something to run against. `evaluation_type` for coding remains
  `manual` for now — test-execution grading is unbuilt, tracked
  separately, not silently assumed here.
- Converted 5 of the new reasoning tasks (marbles, age ordering, chickens
  and cows, day-of-week, clock angle) to `exact_match`, since each has one
  short, unambiguous correct answer. The chickens-and-cows prompt was
  narrowed to ask for cows only, since `exact_match` can't verify a
  two-number answer. The rest of reasoning (including reasoning-006,
  left manual on purpose even though its answer is one word) stays
  `manual` — a seating puzzle and a mislabeled-boxes puzzle both have a
  short "final answer" but an open-ended derivation, where a partial
  auto-check would misleadingly imply the whole response was validated.
- Fixed `debugging-009` (`is_anagram`)'s prompt to state explicitly that
  comparison should ignore case and whitespace, removing the spec
  ambiguity that made the original "correct" answer a judgment call.
  `debugging-007` (`second_largest`) has a similar ambiguity (undefined
  behavior on all-duplicate input) that was flagged but not fixed, since
  fixing it wasn't in scope for this round.

Still short of what a learned router would need — see the V3
data-readiness reviews in `docs/case-study/` for what "enough" means.
