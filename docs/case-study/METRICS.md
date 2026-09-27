# Metrics

The measured numbers behind the project's core claims: cost reduction,
latency reduction, and quality retention from routing versus always using
a single strongest model.

## Rule

Every number in this file must trace back to a specific experiment run
recorded in `experiments/` and referenced from `EXPERIMENTS.md`. No
estimated, illustrative, or "expected" figures — an empty section is
correct until real data exists.

## Metrics tracked (once measured)

- Cost per request/task, routed vs. single-model baseline.
- Latency per request/task, routed vs. single-model baseline.
- Evaluation/quality score, routed vs. single-model baseline.
- Escalation rate (V2+): how often the router defers to a stronger model.

## Status

Real, measured — 92-task real-Groq-data leave-one-out cross-validation,
2026-09-27 (full detail: `docs/case-study/EXPERIMENTS.md`, same date;
source: `backend/app/routing/learned/artifacts/learned-v2.manifest.json`,
reproducible via `python scripts/train_router.py`).

| strategy | accuracy | cost vs always-120b | latency vs always-120b | 120b usage |
|---|---|---|---|---|
| always-20b | 88.0% | 0.54x | 0.70x | 0% |
| always-120b | 90.2% | 1.00x | 1.00x | 100% |
| D2 baseline (preferred) | 90.2% | 0.55x | 0.70x | 6.5% |
| learned-v2 (V3) | 88.0% | 0.63x | 0.74x | 23.9% |
| oracle (theoretical ceiling, not implementable) | 93.5% | 0.55x | 0.71x | 5.4% |

**Headline result:** D2 matches always-120b's accuracy (90.2%) while
cutting nominal cost 45% and latency 30%, by sending only 6.5% of
requests to the larger model. Actual billed cost for every strategy:
$0.00 (Groq free tier, no payment method on the account) — the cost
column above is nominal (registry pricing x real token counts), the
real, structural saving is in usage/latency, not a dollar figure yet.

V3's learned router (`learned-v2`) does not currently beat D2 — see
`DECISIONS.md` (2026-09-27) for why, and why that's still a complete,
honestly-reported result.
