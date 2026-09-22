# V3 routing strategy comparison

Generated from `backend/app/routing/learned/artifacts/learned-v1.manifest.json`, trained 2026-09-22T03:52:31.685943+00:00. Evaluated via leave-one-out cross-validation (n=24 too small for a held-out split) against the 24 real (mock + one real-provider) task outcomes that exist in this repo — not simulated, not projected. See docs/case-study/EXPERIMENTS.md (2026-09-22) for the full interpretation.

| Strategy | Accuracy (evaluable) | Avg cost/task | Total cost | Unevaluable |
|---|---:|---:|---:|---:|
| learned-v1 (this V3 model) | 56.5% | $0.000013 | $0.000310 | 1/24 |
| always-cheapest (mock-fast-v1) | 58.3% | $0.000002 | $0.000058 | 0/24 |
| always-strongest (mock-accurate-v1) | 95.8% | $0.000073 | $0.001755 | 0/24 |
| V1/V2 rule-based router | 75.0% | $0.000041 | $0.000986 | 0/24 |
| random (expected value) | 72.9% | $0.000032 | $0.000772 | 0/24 |

**Unevaluable** = the strategy picked a model with no recorded outcome for that task (never guessed as correct/incorrect — reported as unknown).

## Headline finding

`learned-v1` is dominated by `always-cheapest` — worse accuracy at higher cost. It also loses to random selection and to the V1/V2 rule-based router. At n=24 training rows, this decision tree has not learned a useful pattern; it has fit noise. Not recommended for real use. Full root-cause discussion in `docs/case-study/EXPERIMENTS.md`.
