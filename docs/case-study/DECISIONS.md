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
