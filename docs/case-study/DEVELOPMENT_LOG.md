# Development log

A running, dated log of meaningful work sessions: what was done, what was
learned, what's next. This is the raw material the rest of the case study
gets distilled from — terser and more frequent than `PROJECT_STORY.md`.

## What belongs here

- One entry per meaningful work session (not every commit).
- What was attempted, what actually happened, and any surprises.
- Links to relevant commits/PRs where useful.

## Format

```
## YYYY-MM-DD — short title

What was done. What was learned. What's next.
```

## Log

## 2026-09-18 — Project bootstrap

Established the repository foundation before any product functionality:
directory structure (`frontend/`, `backend/`, `benchmarks/`, `experiments/`,
`docs/`, `scripts/`), a minimal FastAPI backend (health check only), a
minimal Next.js/TypeScript frontend (single status page), `CLAUDE.md`,
`PROJECT_STATE.md`, this case-study structure, root `README.md`,
`.gitignore`, and `.env.example`. No routing, provider, benchmarking, or
evaluation logic was implemented. Verified the backend starts and its
tests pass, and that the frontend builds. Next: design and implement V0
(model performance benchmarking).
