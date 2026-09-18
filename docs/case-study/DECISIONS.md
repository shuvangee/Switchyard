# Decisions

A record of significant technical decisions: what was chosen, what the
alternatives were, and why. Optimized for defending choices in a technical
interview — every entry should be answerable with "here's why, and here's
what I gave up."

## Format

```
## YYYY-MM-DD — Decision title

**Decision:** what was chosen.
**Alternatives considered:** what else was on the table.
**Reasoning:** why this option, given the constraints at the time.
**Trade-offs accepted:** what this gives up.
```

## Log

## 2026-09-18 — Repository split: frontend / backend / benchmarks / experiments / docs

**Decision:** Separate the Next.js UI, the FastAPI/Python engine, benchmark
task data, experiment results, and documentation into top-level
directories rather than a single mixed-language app or a monorepo tooling
setup (Nx/Turborepo).

**Alternatives considered:** A single Python app serving both API and
server-rendered UI; a monorepo with shared tooling/build orchestration.

**Reasoning:** The core research work (routing, evaluation, benchmarking)
is Python-side and needs to be usable independently of any UI (scripts,
notebooks, CI). A plain directory split keeps that possible with zero
tooling overhead, and is simple enough to not need justification revisited
later. Monorepo tooling would add setup cost with no current benefit at
this scale.

**Trade-offs accepted:** No shared type definitions between frontend and
backend (acceptable — the API contract is small); no unified build command
(acceptable — each side is run independently in development).

## 2026-09-18 — SQLite for persistence

**Decision:** Use SQLite for all persistence in early versions.

**Alternatives considered:** PostgreSQL from the start.

**Reasoning:** Single developer, local development, no concurrent-write
requirement yet, and zero operational/hosting cost. The persistence layer
is kept behind `backend/app/db/` so a later migration is a contained
change rather than a rewrite, if a real need for it ever appears.

**Trade-offs accepted:** Will not reveal concurrency issues that a
client/server database would surface; acceptable since current scale is a
single developer running benchmark experiments, not concurrent production
traffic.

## 2026-09-18 — Provider adapter interface before any real provider integration

**Decision:** Structure `backend/app/providers/` as an adapter interface
from the start, even though no provider (real or mock) is implemented in
this bootstrap.

**Alternatives considered:** Calling an SDK (e.g. the OpenAI client)
directly from routing code once that code is written, and introducing an
interface later if multi-provider comparison turns out to be needed.

**Reasoning:** The research question is explicitly about comparing models
*across* providers, and development must be possible without paid API
usage. Both requirements need an adapter interface with a mock
implementation; retrofitting one after routing/evaluation code already
depends on a specific SDK would touch every call site.

**Trade-offs accepted:** A small amount of upfront abstraction before it
has a second implementation to justify it — accepted here because the
need is already known, not speculative.

## 2026-09-18 — SQLAlchemy 2.0 (sync engine), no migrations tool yet

**Decision:** Use SQLAlchemy 2.0's declarative ORM with a plain
synchronous engine/session, and `Base.metadata.create_all()` at startup
instead of a migrations tool (Alembic).

**Alternatives considered:** Raw `sqlite3` with hand-written SQL; an async
engine (`asyncpg`-style); adding Alembic from day one.

**Reasoning:** FastAPI request volume at V0 scale doesn't need async DB
access to stay responsive, and a sync engine is simpler to reason about
and test. The ORM gives typed models and relationships (used directly by
`ExperimentRunORM.executions`) for less code than hand-written SQL, with
better test ergonomics (an isolated in-memory database per test, via
`StaticPool`). `create_all()` is sufficient because the schema has no
production data yet to migrate — Alembic is worth adding the moment a real
schema change needs to preserve existing rows.

**Trade-offs accepted:** No migration history; adding a column later means
writing one by hand or introducing Alembic at that point.

## 2026-09-18 — File-authored config synced into SQLite (tasks and models)

**Decision:** Benchmark tasks (`benchmarks/tasks/*.json`) and the model
registry (`backend/app/providers/registry.py`) are both authored as plain
files/code — not edited through the database — and upserted into their
respective tables (`benchmark_tasks`, `model_configs`) at startup, keyed
by id.

**Alternatives considered:** Making the database the source of truth
(admin UI or direct inserts to add a task/model); keeping both purely
in-memory with no DB table at all, joining by id in application code
instead of via SQL foreign keys.

**Reasoning:** Tasks and the model list are engineering artifacts that
belong in git history (reviewable diffs, meaningful commit messages) — not
hidden in database rows. But `ExperimentRunORM`/`ModelExecutionORM` need
real foreign keys to join against for the API and future analytics, which
an in-memory-only approach can't give cleanly. Syncing on startup gets
both: git as the source of truth, SQL as the query/join layer.

**Trade-offs accepted:** A task/model file edit isn't visible until the
next backend restart (no hot reload); if the sync step silently failed,
the DB copy could drift from the files — mitigated by making sync a hard
dependency of startup (the app won't serve requests if it fails) and by
the loader validating every file before any row is written.

## 2026-09-18 — Mock provider: naive real heuristics, not hidden answers

**Decision:** The mock provider's three model profiles differ by
*capability* (a "basic" vs "capable" naive text-processing heuristic per
task type: single-integer-only arithmetic vs. also handling negatives/
decimals, a short sentiment keyword list vs. a longer one, first-regex-
match extraction vs. cue-phrase-targeted extraction) rather than by being
handed the task's `expected_output` and probabilistically corrupting it.

**Alternatives considered:** Give the mock provider the expected answer
and a per-profile "accuracy" probability of returning it correctly
(simpler to implement, and easy to tune to any target accuracy).

**Reasoning:** A provider that peeks at the expected output isn't
simulating a model — real models never see the grading key. Deriving
correctness from an honestly-limited (but real) capability means the mock
fails for the same *kind* of reason a real small/cheap model would (can't
parse a decimal, doesn't recognize a subtler sentiment word, grabs the
wrong regex match), which is a more defensible stand-in for the thing V0
is trying to measure, and it composes correctly with future real
providers without special-casing.

**Trade-offs accepted:** Harder to hit an exact target accuracy number
(e.g. "exactly 70% correct") since correctness is emergent from the
heuristic and the specific task, not a dial. Also means the mock's
prompt-sniffing is tuned to this repo's specific sample tasks and is not a
general NLP system — documented directly in `mock.py`'s module docstring.

## 2026-09-18 — Synchronous experiment execution, no job queue

**Decision:** `run_experiment()` executes every (task, model) pair
in-process and returns only once the whole run is complete; there is no
background worker or job queue.

**Alternatives considered:** A task queue (Celery/RQ) with polling or
websocket updates for run progress.

**Reasoning:** V0's scale is a handful of tasks times a handful of models
per run — milliseconds to low seconds even with the "slow" mock profile.
A queue would add a broker dependency and a whole new failure mode (a
worker not running, message loss) to solve a problem that doesn't exist
yet. CLAUDE.md's engineering principles are explicit about this: add
complexity only when a version's actual requirements demand it.

**Trade-offs accepted:** A run against enough tasks/models/real (slow,
rate-limited) providers to take a long time will block the HTTP request
for that whole duration. Revisit if/when real provider runs at meaningful
scale make that actually painful — not before.

## 2026-09-18 — httpx over the official OpenAI SDK for the real adapter

**Decision:** `OpenAIProvider` calls the Chat Completions endpoint
directly with `httpx.post()` rather than the `openai` Python package.

**Alternatives considered:** The official `openai` SDK.

**Reasoning:** The adapter needs exactly one thing (a chat completion with
usage numbers), and `httpx` was already a dependency (FastAPI's test
client uses it). Adding the full SDK for one endpoint is more surface area
than the `Provider` interface actually needs, and the interface already
insulates the rest of the app from this choice — switching to the SDK
later is a one-file change.

**Trade-offs accepted:** No SDK conveniences (retries, streaming, typed
request/response models) — acceptable since none of those are used yet,
and this adapter is disabled by default and has never been called against
the real API in this environment (verified only via mocked HTTP calls).

## 2026-09-18 — V1 rules instead of ML, and why now

**Decision:** V1 routes with a small, explicit, ordered list of rules
(category + difficulty → model, each with a plain-text rationale) rather
than any learned model.

**Alternatives considered:** Training even a simple classifier (logistic
regression on category/difficulty/prompt features → model choice) now
that V0 produces labeled data.

**Reasoning:** Two independent reasons, not one. First, the roadmap is
explicit that V3 is where learned routing belongs, evaluated against a
rule-based baseline — building that baseline is V1's actual job. Second,
and more importantly: V0's only evidence is from the mock provider, and
training anything on it would be learning the mock's own hard-coded
basic-vs-capable heuristics, not a real pattern — a genuinely pointless
model. A rule the size of "easy deterministic task → cheap model" is
already the full extent of what 12 mock-provider tasks can responsibly
support; a learned model would suggest a confidence the data doesn't have.
Rules are also the only choice that satisfies the routing decision
record's rationale requirement honestly — a rule's rationale is the actual
reason; a model's "rationale" would have to be reverse-engineered or
fabricated after the fact.

**Trade-offs accepted:** Won't discover routing patterns finer than what's
hand-derived from the baseline (e.g. per-task rather than per-category
signals) — acceptable, since finer patterns need finer evidence, which
doesn't exist yet either.

## 2026-09-18 — Routing rules as one Python data list, not a config format

**Decision:** `DEFAULT_RULES` in `backend/app/routing/rules.py` is a plain
Python list of frozen `RoutingRule` dataclasses — declarative data
(categories, difficulties, model_id, rationale), not a YAML/JSON DSL with
its own parser.

**Alternatives considered:** An external rules file (YAML/JSON) loaded and
validated at startup, mirroring the benchmark-task-file pattern.

**Reasoning:** The benchmark-task-file pattern is right for benchmark
tasks because non-engineers plausibly add tasks and because they need to
be data, loadable and diffable independent of code. Routing rules are
reviewed and changed by whoever is also changing the router's logic, and
matching them against a `RequestAnalysis` already requires code (the
`matches()` method) — introducing a second config format and loader for a
handful of rules add indirection with no one actually needing it yet.
"Do not hard-code rules across random files" is satisfied by having
exactly one file define them, not by which file format that file uses.

**Trade-offs accepted:** Adding or changing a rule requires a Python
change (and redeploy) rather than an edit to a data file — acceptable at
V1's scale (3 rules); revisit if rules need to be editable without a code
change (e.g. by a non-engineer, or at runtime).

## 2026-09-18 — Difficulty estimated by word count, and its known failure mode

**Decision:** `RequestAnalysis.difficulty` is estimated purely from prompt
word count (≤20 words easy, ≤60 medium, else hard) — the simplest possible
proxy, with no claim that it reflects real task difficulty.

**Alternatives considered:** Reusing category-specific signals from the
mock provider itself (e.g. "contains a negative number" for math); an LLM
call to estimate difficulty (rejected outright — adds cost and a second
model call before the router has even chosen one).

**Reasoning:** Word count is transparent, free, and instantly explainable
to a user reading a routing rationale ("this was a short prompt") — which
matters more at V1 than being right, given V1's entire premise is
explainability over accuracy. Category-specific proxies were rejected
specifically to avoid a difficulty estimator that secretly knows how
MockProvider works internally, which would silently stop meaning anything
once a real provider is added.

**Trade-offs accepted, discovered directly during verification:** this
heuristic genuinely misroutes requests. "What is -8 + 15?" (5 words) is
estimated easy and routed to `mock-fast-v1`, which gets it wrong (23,
having ignored the minus sign) — because word count says nothing about
numeric complexity. A longer rephrasing of the identical problem crosses
into "medium" purely by word count and is routed correctly. See
`FAILURES_AND_LESSONS.md` for the full example. Not fixed here — patching
it with a category-specific rule (e.g. "math + contains a minus sign =
hard") would be tuning the analyzer to MockProvider's internals again,
the exact thing this decision avoids. The honest fix needs either a real
difficulty signal or (V2) confidence/escalation that can catch a wrong
answer after the fact rather than trying to predict it beforehand.

## 2026-09-18 — Routing decision and execution result share one table

**Decision:** `RequestLogORM` holds the request's analysis, routing
decision, and execution result (response/error, latency, tokens, cost) as
one row, rather than a routing-decisions table joined to an
executions-style table.

**Alternatives considered:** Reusing the `ModelExecutionORM` shape (as
used for benchmark runs) plus a separate `RoutingDecisionORM`, joined 1:1.

**Reasoning:** A benchmark execution belongs to an experiment run and a
benchmark task — genuine many-to-one relationships worth a foreign key
each. A routed Playground request has exactly one routing decision and
exactly one execution, always, with no case where they vary
independently. Splitting a strict 1:1 relationship into two tables joined
by id buys normalization with no actual flexibility in return.

**Trade-offs accepted:** `RequestLogORM` and `ModelExecutionORM` duplicate
several columns (status, latency_ms, tokens, cost) with no shared base —
acceptable; they represent different things (a benchmark-task execution
vs. a live routed request) that happen to share a shape, not the same
concept wearing two tables.
