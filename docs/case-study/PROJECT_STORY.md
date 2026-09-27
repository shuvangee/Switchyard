# Project story

The five-minute version of Switchyard. For the full narrative (15
sections, results table, limitations), see `WEBSITE_CASE_STUDY.md`; for
the exhaustive technical record, see `DECISIONS.md`,
`DEVELOPMENT_LOG.md`, `EXPERIMENTS.md`, and `FAILURES_AND_LESSONS.md`.

## The problem

Sending every request to the strongest model is wasteful; sending every
request to the cheapest model risks quality. Switchyard exists to build a
real routing system between those extremes and measure — not assume —
the trade-off.

## The research question

Can task-aware routing preserve answer quality while reducing cost and
latency?

## How the approach changed as real results came in

The project started with mock providers and a rule-based router (V1),
added validation/escalation (V2), then built and evaluated a learned
router (V3) expecting it to outperform the simple rules. It didn't: a
one-line rule ("D2" — route summarization to the larger model, everything
else to the smaller one), validated with leave-one-out cross-validation,
matched the larger model's measured accuracy while using it only 6.5% of
the time. A trained decision tree evaluated the same rigorous way reached
88.0% LOOCV accuracy against D2's 90.2% — a real, reported negative
result, not hidden or retrained away. Full account: `WEBSITE_CASE_STUDY.md`
sections 08-10.

## Current state

V4 (final product/deployment stage). D2 is the preferred production
router; `learned-v2` stays fully integrated and selectable for direct
comparison. See `PROJECT_STATE.md` for the current stage in detail.
