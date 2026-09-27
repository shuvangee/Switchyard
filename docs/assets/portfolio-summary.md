# Portfolio summary

Source material for a portfolio site, resume, or interview — every claim
below is backed by `docs/case-study/METRICS.md` and reproducible via
`docs/case-study/EXPERIMENTS.md`. Nothing here is written to sound better
than the measured result.

## Concise project description

Switchyard is an adaptive multi-model AI routing system: instead of
sending every request to the same model, it analyzes each request and
routes it to the model that fits it, then measures the actual cost,
latency, and quality trade-off instead of assuming one. Built end-to-end
— benchmark design, real-model evaluation, a rule-based production
router, and a trained learned-routing alternative, evaluated with
leave-one-out cross-validation and compared head-to-head. The project's
central finding was a negative result reported honestly: the learned
router did not beat the simple rule, and the simple rule shipped as the
preferred production strategy instead.

## Resume bullets

- Built and shipped an adaptive multi-model AI request router (FastAPI /
  Next.js) that matched a larger model's measured accuracy (90.2%) while
  routing only 6.5% of benchmark requests to it, cutting nominal cost
  45.5% and average latency 29.8% — validated with leave-one-out
  cross-validation on a 92-task real-model benchmark, not assumed.
- Designed and built a 104-task, 8-category LLM evaluation benchmark
  with six distinct automated grading methods (exact match, execution-
  based sandboxed grading, structured-output validation, required-fact
  checks, among others), reaching 92/104 automated coverage while
  documenting the remaining 12 as genuinely non-deterministic rather
  than forcing a fake pass/fail.
- Trained and rigorously evaluated a learned routing classifier against
  a simple rule-based baseline using leave-one-out cross-validation and
  system-level outcome scoring; reported the honest result that the
  learned model did not outperform the rule (88.0% vs. 90.2% accuracy)
  and shipped both, with the simpler strategy as the production default.

## Short interview explanation

"I built a system that routes AI requests to the cheapest model that can
handle them, escalating to a bigger model only when the evidence says
it's worth it. I benchmarked two real models across 104 tasks, then
built two different routing strategies: a simple one-line rule and a
trained decision tree. I expected the learned model to win — it didn't.
Evaluated the same rigorous way on the same held-out data, the simple
rule matched the bigger model's accuracy using it only 6.5% of the time,
while the learned router used the bigger model almost four times more
often and still scored lower. The most useful part of the project wasn't
the routing policy — it was the discipline of evaluating both approaches
identically and reporting that the more sophisticated one lost, instead
of tuning it until it won."

## Assets in this directory

- `architecture-diagram.mmd` / `architecture-training-diagram.mmd` —
  Mermaid source for the two diagrams in `docs/architecture/overview.md`
  and the README, renderable standalone (e.g. the Mermaid Live Editor or
  any Mermaid-aware Markdown viewer).
- `results-comparison.json` — the same strategy-comparison data shown on
  the Compare page, as flat JSON for a portfolio site's own chart.
- `screenshots/overview.png` — the Overview page, leading with the
  measured headline result.
- `screenshots/compare.png` — the Compare page: all five strategies, the
  oracle visually and textually marked as a theoretical upper bound.
- `screenshots/playground-routing-trace.png` — a real routing trace
  captured in this deployment's own demo mode (no Groq key configured):
  D2 correctly selects `groq-gpt-oss-120b` for a summarization request,
  falls back to the mock tier because no real provider is available, and
  still returns a real, successful, fully-traced response. Not a staged
  mockup — an actual screenshot of the running application.
