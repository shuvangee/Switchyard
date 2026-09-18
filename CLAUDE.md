# CLAUDE.md

Permanent engineering instructions for anyone (human or Claude Code) working
on this repository. Read this before making non-trivial changes, and read
`PROJECT_STATE.md` before starting on anything beyond a small fix.

## What Switchyard is

Switchyard is an adaptive multi-model AI routing system. Instead of
sending every request to the same model, it analyzes each task and routes
it to whichever available model is the right fit, weighing task type,
task difficulty, expected answer quality, model capability, inference
cost, response latency, reliability, context requirements, and historical
performance.

## The research question

Can an intelligent routing system significantly reduce AI inference cost
and latency without meaningfully reducing answer quality?

Everything in this repository — architecture, benchmarks, experiments,
documentation — exists in service of answering that question with real
measurements. This is being built as (1) a serious AI engineering
portfolio project, (2) an engineering research case study, and (3) a
project defensible in depth in technical interviews. Treat it accordingly:
not a toy API wrapper, but also not an overengineered platform.

## Version roadmap

Build incrementally. Do not skip ahead or implement a later version's
functionality "while you're in there."

- **V0 — Model performance benchmarking.** Establish benchmark tasks and
  measure raw model performance (quality, cost, latency) with no routing
  logic yet.
- **V1 — Rule-based multi-model routing.** Route requests using explicit,
  explainable rules based on V0 data.
- **V2 — Evaluation, confidence, fallback, and escalation.** Score
  response quality, add confidence estimation, and let the router escalate
  to a stronger model when warranted.
- **V3 — Learned routing.** Replace or augment rules with a learned
  routing policy, evaluated against the V1/V2 baseline.
- **V4 — Production-style analytics, observability, and polish.** Harden
  the system and finish the case study.

## Engineering principles

1. Prefer simple architectures before complicated ones. Add complexity
   only when a version's actual requirements demand it.
2. Keep frontend and backend concerns strictly separate.
3. Keep provider implementations modular, behind the adapter interface in
   `backend/app/providers/` — never import a vendor SDK from routing,
   evaluation, or experiment code directly.
4. Keep routing strategies replaceable behind a common interface so
   strategies can be compared, not just swapped.
5. Add type annotations where reasonable (Python type hints, TypeScript
   types) — this is a project meant to read like production-quality
   engineering.
6. Add tests for meaningful logic (routing decisions, evaluation scoring,
   provider adapters). Do not write tests for trivial glue code just to
   pad coverage.
7. No premature abstraction: don't build for a hypothetical future
   version. Three similar lines beat a speculative helper.
8. Business logic lives in `backend/app/`, organized by responsibility
   (`routing/`, `providers/`, `evaluation/`, etc.) — never scattered across
   route handlers or frontend code.
9. Do not introduce Kubernetes, microservices, message queues, Redis, or
   other heavy infrastructure unless a later version genuinely requires
   it. Justify the requirement in `docs/case-study/DECISIONS.md` before
   adding it.

## Documentation requirements

- **Read `PROJECT_STATE.md` before any major change.** It records the
  current stage, current objective, what's completed, and what's next.
  Update it when that changes.
- **Update the relevant case-study documentation after meaningful work**,
  in `docs/case-study/`:
  - `DEVELOPMENT_LOG.md` — a dated entry per meaningful work session.
  - `DECISIONS.md` — any significant technical decision, with
    alternatives considered and trade-offs accepted.
  - `EXPERIMENTS.md` / `METRICS.md` — real results from real experiment
    runs only.
  - `FAILURES_AND_LESSONS.md` — approaches that didn't work and why.
  - `PROJECT_STORY.md` / `WEBSITE_CASE_STUDY.md` — updated periodically
    once there's a real story/result to summarize, not after every change.
- Document important technical decisions where they're made, not just in
  retrospect.

## Never fabricate

- Never fabricate benchmark results, evaluation scores, or experiment
  output. If a number isn't backed by a real run recorded under
  `experiments/`, it does not go in `METRICS.md`, `EXPERIMENTS.md`, the
  README, or the frontend.
- Never fabricate cost savings or latency improvements.
- Never claim evaluation quality that hasn't actually been measured.
- An empty section in a case-study document (a "no results yet" note) is
  always correct over an invented placeholder number.

## Design rules (frontend)

The UI must read as engineering software — a research workstation /
developer console / observability tool — not a generic AI SaaS landing
page.

Avoid: purple/blue gradient backgrounds, glowing borders, neon,
glassmorphism, animated blobs, sparkles, robot or "AI brain" imagery,
giant gradient headlines, excessive pill-shaped UI, wrapping every section
in a floating rounded card, fake testimonials/logos/usage numbers, and
chatbot bubbles as the primary interface.

Prioritize: typography and hierarchy, intentional whitespace, information
density, tables, technical metadata, clean charts, thin borders, restrained
surfaces, readable status indicators. Use neutral backgrounds, dark
readable text, one restrained primary accent color, status colors only
when semantically meaningful, and monospace selectively for IDs, model
names, costs, latency, and timestamps. Not every section needs a card.

## Product language

Avoid marketing language: "unlock AI," "supercharge," "revolutionary,"
"next-generation intelligence," "AI-powered magic," "transform your
workflow." Use precise terms instead: routing decision, selected model,
request latency, estimated cost, experiment, evaluation score, escalation,
provider, benchmark, router version.

## Cost constraints

This project is built and run on a student budget.

- Development must be possible without paid API usage — use mock
  providers locally.
- Before running a benchmark or experiment that will call paid provider
  APIs, make the expected cost visible (estimated request count × known
  per-token pricing) before executing it.
- Prefer smaller/cheaper models and smaller benchmark sets while
  iterating; scale up deliberately, not by default.

## Interview defensibility

Every non-trivial choice should be explainable: what was chosen, what the
alternatives were, why this one, and what trade-off was accepted. That's
what `docs/case-study/DECISIONS.md` is for — write the entry when the
decision is made, not reconstructed later from memory.

## Git Workflow

Git history is part of the Switchyard case study and should clearly show how the project evolved.

### Automatic Commits

After completing each self-contained logical unit of work, automatically create a Git commit.

Do not wait until the end of the entire session.

A logical unit may include:
- implementing one feature
- fixing one bug
- adding or modifying one subsystem
- adding a meaningful group of tests
- completing one refactor
- completing one documentation/case-study update
- completing one project setup/configuration task

Do NOT create a separate commit for every individual file edit if multiple files belong to the same logical change.

For example:

GOOD:

feat: add benchmark task schema

feat: implement mock model provider

feat: add experiment execution pipeline

test: add experiment runner coverage

docs: document V0 benchmark architecture

BAD:

chore: edit schema.py

chore: edit database.py

chore: edit README

chore: edit file again

Commits should represent meaningful project history.

### Before Every Commit

Before creating a commit:

1. Review `git status`.
2. Review the changes being committed.
3. Make sure unrelated changes are not accidentally included.
4. Run the relevant tests/checks for that unit of work.
5. Verify that no secrets, API keys, `.env` files, credentials, generated junk, or sensitive files are being committed.
6. Update relevant documentation if the change requires it.
7. Stage only the files belonging to that logical unit.
8. Create the commit.

Do not knowingly commit broken code unless I explicitly request a checkpoint/WIP commit.

If tests fail because of the current work:
- fix the failure
- rerun the relevant tests
- commit only after the unit is in a valid state

If a test failure is unrelated and existed before the current task:
- document that clearly
- do not silently modify unrelated code merely to obtain a green test run

### Commit Message Format

Use Conventional Commits.

Preferred types:

- `feat:` new functionality
- `fix:` bug fix
- `test:` tests
- `docs:` documentation
- `refactor:` internal code improvement without behavior change
- `perf:` performance improvement
- `chore:` tooling, setup, configuration, dependencies
- `ci:` CI/CD changes
- `build:` build-system changes

Commit messages should be concise and describe the actual change.

Examples:

`chore: initialize Switchyard project structure`

`feat: add benchmark task schema`

`feat: implement mock provider adapter`

`feat: add experiment execution pipeline`

`fix: continue experiment after provider failure`

`test: add provider failure coverage`

`docs: record V0 architecture decisions`

`refactor: separate provider registry from experiment runner`

Avoid vague messages such as:

`update stuff`

`changes`

`fix`

`working version`

`final`

### Commit Scope

Keep commits reasonably atomic.

Code, tests, and documentation that all belong to the same feature may be included in the same commit.

Example:

A new benchmark runner may include:
- implementation
- tests
- associated schema changes
- documentation directly required by the feature

These may be committed together as:

`feat: add benchmark experiment runner`

Do not mix unrelated work into the same commit.

### Case Study Commits

When a development task creates meaningful case-study information, update the relevant documentation before finishing that logical unit.

Examples include:

- `PROJECT_STATE.md`
- `docs/case-study/DEVELOPMENT_LOG.md`
- `docs/case-study/DECISIONS.md`
- `docs/case-study/EXPERIMENTS.md`
- `docs/case-study/FAILURES_AND_LESSONS.md`
- `docs/case-study/METRICS.md`

Minor documentation directly associated with a feature can be included in the same feature commit.

Larger standalone case-study updates should use a separate `docs:` commit.

### Never Push Automatically

NEVER run:

`git push`

or otherwise push commits to a remote repository unless I explicitly ask you to push.

Creating local commits is authorized.

Pushing is not.

Do not create pull requests, merge branches, force-push, rebase published history, or modify remote branches unless explicitly requested.

### Git Safety

Never use destructive Git operations without explicit permission.

Do not automatically run commands such as:

- `git reset --hard`
- `git clean -fd`
- `git push --force`
- destructive rebases
- deleting branches
- discarding user changes

Preserve any existing user-authored changes.

If unrelated uncommitted changes already exist, do not overwrite or accidentally include them. Keep your changes isolated where possible.

### Git Identity

If Git cannot create a commit because `user.name` or `user.email` is not configured:

- stop the commit
- tell me what configuration is missing
- do not modify my global Git identity automatically

### End-of-Task Report

After each logical unit, tell me:

- what was completed
- tests/checks run
- commit message
- short commit hash

At the end of a larger task or version, also show the commits created during that work.

Do not push them.
