# Switchyard: adaptive multi-model AI routing

A case study in building a routing system, measuring it honestly, and
reporting a negative result instead of hiding it.

## 01. The problem

Most applications that call an LLM send every request to the same model.
That's simple, but it's wasteful in one direction and risky in the
other: routing everything to the strongest available model spends money
and latency on requests that didn't need it, while routing everything to
the cheapest model risks quality on the requests that did. The interesting
engineering question isn't "which model is best" — it's whether a system
can look at a request before running it and make a good enough guess
about which model it actually needs.

## 02. Hypothesis

**Can task-aware routing preserve answer quality while reducing cost and
latency?** Not "can routing help in theory" — that's assumed by half the
AI infrastructure industry already. The point of this project was to
build a real routing system, benchmark it against real models, and
measure the actual trade-off instead of asserting one.

## 03. Building the benchmark

Before any routing logic existed, Switchyard needed something to route
*for* — real tasks with a defensible way to check whether a model got
them right. Benchmark tasks were authored across eight categories
(extraction, classification, summarization, math, reasoning, coding,
debugging, structured output), each with an explicit `evaluation_type`
so grading method was a first-class decision, not an afterthought. The
first version of the benchmark started small; it grew to 104 tasks over
the course of the project as gaps in category coverage and evaluation
signal became visible (see 06).

An early architectural choice mattered more than it looked at the time:
routing rules, evaluation strategies, and provider integrations were each
kept behind their own interface from day one — a provider adapter
(`app/providers/`), an evaluation strategy registry, and a router-version
dispatch string rather than a class hierarchy. None of that complexity
was needed for a V0 mock benchmark. It became necessary the moment a
second real provider and a second routing strategy showed up, and having
built it early meant nothing had to be retrofitted.

## 04. Moving from mock models to real models

V0 ran entirely on mock providers — deterministic fast/cheap and
slow/accurate profiles — so the benchmark harness, evaluation strategies,
and experiment runner could all be built and tested with zero API cost.
That discipline held throughout the project: nothing paid ever ran
without the cost being made visible first.

The first real-provider experiment (Gemini, 2026-09-20) was where the
project stopped being a simulation. It immediately surfaced a problem
that mock data could never have shown: the evaluators built against mock
model output were too naive for a real model's actual response style,
undercounting correctness that a human would have accepted. A real free
tier also came with real constraints — 20 requests/day per model, and
"thinking" tokens that silently ate into the answer — both of which
shaped how later benchmark runs were scheduled and parsed. A near-loss of
18 already-captured real responses during a re-run of the generation
script was a hard lesson in treating expensive real-model output as data
to protect, not something regeneratable on demand.

Groq was added shortly after as the model pair the project would actually
route between (`groq-gpt-oss-20b` / `groq-gpt-oss-120b`), and the
benchmark was expanded from 44 to 104 tasks alongside it — catching four
real bugs in the process (extraction and grading logic that had never
been exercised against real model phrasing).

## 05. Evaluation problems we discovered

Real model output broke assumptions the mock-based evaluators had gotten
away with. "A valid label" turned out not to be the same thing as "the
correct label" — a classification response could pick a real, well-formed
option from the list and still be wrong, and the earliest evaluator
couldn't tell the difference. Coding and debugging tasks needed actual
execution-based grading, not string comparison, which meant building a
sandboxed grader (no network, no filesystem access outside a temp dir)
rather than trusting a regex against source code. And at least one
debugging task turned out to have no defensible automated answer at all
— its only discriminating test input had an undefined correct output, so
grading it automatically would have meant the grader silently resolving
an ambiguity the task was supposed to test. That task, and several
similar summarization tasks, were left manual-only rather than forced
into a fake pass/fail.

## 06. Improving evaluation coverage

A dedicated pass (internally "V2.6") went category by category asking
whether each task's grading method was actually defensible, and closed
the gaps that could be closed: sandboxed execution grading for
coding/debugging (36/36 once a real extraction bug in the grader itself
was caught and fixed), required-fact presence checks for summarization,
and a routing-opportunity analysis to confirm the 20B/120B pair actually
disagreed often enough to be worth routing between before spending more
effort training anything. The honest result of that pass: 92 of 104
tasks reached automated grading; 12 could not, for real, documented
reasons rather than lack of effort. That 92/12/0 split is the same
coverage number the shipped product shows today — no task was quietly
dropped to make the ratio look better.

## 07. First routing opportunity

Before building any learned routing, the project asked a more basic
question: does this model pair even disagree enough for routing to
matter? The routing-opportunity analysis answered that directly on the
now-92-task graded set: the two models' correctness differed on a real
but small number of tasks. That number — not a guess — is what shaped
every routing decision after it, including the eventual finding that a
learned classifier would have very little signal to learn from (see 10).

## 08. The D2 rule

With real per-task correctness data for both models in hand, a family of
simple, fully-auditable routing rules was tried and evaluated with
leave-one-out cross-validation before any learned model was trained. One
category stood out: summarization was the one place the larger model
showed a real, cross-validated accuracy edge. That produced "D2": route
summarization to `groq-gpt-oss-120b`, everything else to
`groq-gpt-oss-20b`. One line, no training data, no hidden state — and it
matched `always-120b`'s accuracy (90.2%) while sending only 6.5% of
requests to the larger model. D2 became the project's preferred
production strategy from that point forward.

## 09. Training a learned router

D2 being simple didn't mean the project stopped there — the natural next
question was whether a learned model could do better by using more
signal than one category flag. A shallow decision tree (`learned-v2`) was
trained to predict whether a given request should escalate from the 20B
model to the 120B model, using only features available before execution
(category, difficulty, structured-output flag, estimated tokens — the
same features every router in the system already computes). It was
evaluated the same way D2 was: leave-one-out cross-validation over the
same 92 real-graded tasks, scored on system-level outcome (the actual
cost/latency/correctness of whichever model it picked), not on
classifier accuracy against a label in isolation. Logistic regression
edged it out by exactly one task in raw accuracy while escalating to the
120B model nearly twice as often — treated as noise at this sample size,
and the decision tree was kept for its interpretability and lower cost.

## 10. Why learned routing lost

`learned-v2` reached 88.0% LOOCV accuracy. D2 reached 90.2% — on the same
92 tasks, using the larger model 6.5% of the time against learned-v2's
23.9%. The learned router used more of the expensive model and still
answered fewer requests correctly.

The most likely explanation is data, not algorithm choice: the two
models' correctness only actually differed on 8 of the 92 graded tasks (5
of them positive "should escalate" examples). That is too little signal
for a learned classifier to reliably find a better policy than the
single-category rule D2 had already found by inspection. This was the
project's central and most important finding — **more sophisticated
machine learning was not automatically better when the routing signal
itself was sparse.** It's reported here exactly that way rather than
softened, buried, or quietly fixed by retraining until the numbers moved:
`learned-v2` is fully integrated and selectable for direct comparison in
the shipped product, not deleted, and it stays second to D2 in every
place the project makes a production recommendation.

## 11. Final system

The shipped system routes through a single dispatch point
(`app/routing/service.py`) that's agnostic to which strategy picked the
model: D2 (preferred), learned-v2 (comparison), fixed always-20b/120b
baselines (comparison), and the original V1/V2 rule-based router (kept
for history). Every routed request is analyzed, routed, executed against
a real Groq model (or a mock fallback if no key is configured),
validated, escalated on failure within a bounded retry, and persisted
with a full system-level trace — never hidden model reasoning. The same
committed benchmark results back every real number the product shows on
Overview, Compare, Models, and Benchmarks, so a fresh deployment with an
empty database still shows the real, measured research result rather
than nothing. Full architecture: `docs/architecture/overview.md`.

## 12. Results

Measured on the 92 automatically graded benchmark tasks:

| Strategy | Accuracy | Nominal cost | Avg latency | 120B usage |
|---|---|---|---|---|
| always-20b | 88.0% | $0.008108 | 646ms | 0% |
| always-120b | 90.2% | $0.015020 | 927ms | 100% |
| **D2 baseline (preferred)** | **90.2%** | **$0.008193** | **651ms** | **6.5%** |
| learned-v2 | 88.0% | $0.009477 | 687ms | 23.9% |
| perfect oracle (theoretical upper bound only) | 93.5% | $0.008187 | 655ms | 5.4% |

D2 matched always-120b's measured accuracy while cutting nominal cost by
45.5% and average latency by 29.8%, sending only 6.5% of requests to the
larger model. Actual billed cost across every strategy was $0.00 (Groq's
free tier) — the real, structural result here is the usage and latency
shift, not a dollar figure from a paid account.

## 13. What I learned

The most valuable outcome of this project wasn't a routing policy — it
was proof that a simple, auditable rule can beat a more sophisticated
learned model when it's evaluated the same rigorous way (leave-one-out
cross-validation, system-level outcome, not just label accuracy). It's
easy to assume "learned" beats "rule-based" by default; this project
built the learned version, measured it fairly against the same baseline,
and let the result say otherwise. Committing to that measurement
discipline before knowing which approach would win — same evaluation
method, same held-out protocol, same reported honesty either way — is
the part of this project most worth explaining in an interview.

## 14. Limitations

- The benchmark is small (104 tasks, 92 automatically graded) — not a
  production-scale evaluation set, and a different 92-task sample could
  plausibly shift which strategy wins.
- Only two models are realistic production routing candidates; a third
  registered model (`groq-qwen3.8-27b`) is not called by any router.
- The benchmark's category distribution is authored, not sampled from
  real production traffic, so it may not represent a real deployment's
  request mix.
- 12 tasks still have no defensible automated ground truth.
- Every cost figure here is nominal (published per-token pricing x real
  token counts) — actual billed cost during development was $0.00 on
  Groq's free tier, which says nothing about paid-deployment economics.
- The learned router was trained on only 8 tasks with observed model
  disagreement; that's too small a sample to generalize "learned routing
  doesn't work" beyond this specific dataset.

## 15. Next steps

- Expand benchmark coverage, particularly in categories where the two
  models rarely disagree, before revisiting learned routing with more
  signal to learn from.
- Resolve the 12 manual-only tasks once a defensible automated method
  exists for each, rather than forcing a rubric to close the gap.
- Investigate a third model's marginal value specifically on the small
  set of tasks where both current models fail together, instead of
  general capability claims.
- Move router-comparison analytics from a static training manifest to a
  live recomputation once a real deployment accumulates meaningful
  traffic.

---

Full technical detail behind every claim above: `docs/case-study/DECISIONS.md`,
`EXPERIMENTS.md`, `METRICS.md`, `FAILURES_AND_LESSONS.md`, and
`DEVELOPMENT_LOG.md`. Architecture: `docs/architecture/overview.md`.
Reproducible entry points: the project `README.md`.
