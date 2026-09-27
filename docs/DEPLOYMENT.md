# Deployment

Repository-side deployment configuration for Switchyard. No account,
payment, or external credential has been created as part of this — that
step is left to whoever deploys it, per its own budget and provider
choice. This document verifies the repository is ready, and gives the
concrete steps to actually put it somewhere.

## No Kubernetes, no queues, no managed database

Switchyard is one FastAPI process and one Next.js process. Request
volume (a student research project, not production traffic) doesn't
justify anything heavier — see `CLAUDE.md`'s engineering principles and
`docs/architecture/overview.md`'s "why these choices." SQLite is the
persistence layer; nothing here requires a managed database service.

## Verified production-readiness (this repository, this session)

- **Frontend production build**: `npm run build` in `frontend/` compiles
  cleanly (`next build`, all 11 routes), typechecks, and lints with no
  errors.
- **Backend production startup**: `uvicorn app.main:app` starts cleanly
  with `ENVIRONMENT=production DEBUG=false` and a fresh, empty
  `DATABASE_URL` — table creation and benchmark/model registry sync run
  automatically on startup (`app/main.py`'s `lifespan`), no manual
  migration step.
- **Health endpoint**: `GET /health` returns
  `{"status": "ok", "app": "switchyard", "environment": "..."}` —
  suitable for a platform's health check.
- **Missing credentials fail gracefully**: with no `GROQ_API_KEY` set,
  the app starts normally, the two Groq models are simply listed as
  disabled, and D2/learned-v2/always-20b/always-120b all fall back to
  the mock provider tier with a real, successful (if non-live) response
  — verified directly against a running instance, not assumed. Nothing
  crashes; nothing exposes internal configuration.
- **Learned-router artifact loading**: `learned-v2`'s committed artifact
  (`backend/app/routing/learned/artifacts/learned-v2.joblib` +
  `.manifest.json`) loads correctly under the same production-like
  environment — it's committed to the repo, not generated at deploy
  time.

## Environment variables

See the README's "Environment variables" table for the full list.
Nothing is required to start the app; `GROQ_API_KEY` is the only one
that changes runtime behavior (live vs. demo-mode routing).

Production-specific:

- `ENVIRONMENT` — set to `production` (currently only used for the
  `/health` response and general clarity; no behavior branches on it
  today).
- `DEBUG` — set to `false` in production.
- `DATABASE_URL` — point at a writable path/volume on whichever platform
  hosts the backend; SQLite needs persistent disk, not a managed DB
  service.
- `CORS_ALLOW_ORIGINS` — a JSON array of allowed frontend origins, e.g.
  `CORS_ALLOW_ORIGINS=["https://switchyard.example.com"]`. Defaults to
  `["http://localhost:3000"]`, which must be overridden for any real
  deployment — see `backend/app/core/config.py`.
- `NEXT_PUBLIC_API_BASE_URL` (frontend) — the deployed backend's public
  URL.

## Suggested free-tier deployment shape

Not created as part of this work — named here because CLAUDE.md's cost
constraints prefer a deployment architecture that can use free tiers,
and because the choice affects nothing else in the repo:

- **Frontend**: Vercel (native Next.js support, generous free tier).
- **Backend**: any platform that runs a long-lived process with a
  persistent volume for the SQLite file (e.g. Render's free web service
  tier, Fly.io's free allowance). A platform that only offers ephemeral
  or serverless filesystems will lose the SQLite database on every
  restart/cold start — that's a real constraint of the current
  persistence choice, not a deployment detail to paper over.
- **Groq API key**: optional. Without one, the deployment runs fully in
  demo mode (see above) — a legitimate, intended way to host this
  publicly without paying for inference.

Actually provisioning any of the above requires an account and is left
to whoever deploys this; nothing paid or account-gated was created here.

## Secrets

- `.env` is git-ignored (see `.gitignore`); only `.env.example` (no real
  values) is committed.
- No API key, credential, or `switchyard.db` file is committed anywhere
  in the repository — see `docs/case-study/DECISIONS.md`'s V4 security
  review entry for the specific check performed.
