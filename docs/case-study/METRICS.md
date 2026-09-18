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

No measurements exist yet. This file stays empty of numbers until V0
benchmarking produces real ones.
