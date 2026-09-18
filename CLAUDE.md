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
