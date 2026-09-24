# Simple routing baselines: groq-gpt-oss-20b vs groq-gpt-oss-120b

Evaluated on the 92 tasks with real ground truth for both models (same set as `routing-opportunity-analysis.md`). Every rule below is derived from and scored against this SAME set — **in-sample by construction** — see the generalization section for what that does and doesn't license.

## Phase 1D — category-aware rule (derived from data, not assumed)

| category | n | 20b acc | 120b acc | rule |
|---|---|---|---|---|
| classification | 13 | 84.6% | 92.3% | 120b |
| coding | 13 | 100.0% | 100.0% | 20b (tie -> cheaper) |
| debugging | 12 | 100.0% | 100.0% | 20b (tie -> cheaper) |
| extraction | 13 | 76.9% | 76.9% | 20b (tie -> cheaper) |
| math | 13 | 84.6% | 76.9% | 20b |
| reasoning | 9 | 88.9% | 88.9% | 20b (tie -> cheaper) |
| structured_output | 13 | 100.0% | 100.0% | 20b (tie -> cheaper) |
| summarization | 6 | 50.0% | 83.3% | 120b |

## Phase 1E — difficulty-aware rule (derived from data, not assumed)

| difficulty | n | 20b acc | 120b acc | rule |
|---|---|---|---|---|
| easy | 18 | 94.4% | 100.0% | 120b |
| medium | 44 | 86.4% | 88.6% | 120b |
| hard | 30 | 86.7% | 86.7% | 20b (tie -> cheaper) |

Difficulty's (20b-120b) accuracy gap ranges -5.6% to +0.0% across easy/medium/hard — a 5.6% spread, versus category's spread (see table above). Difficulty alone does not separate the models nearly as cleanly as category does; treating it as a routing signal on its own would be **inventing a pattern the data doesn't clearly support**.

## Phase 1F — category + difficulty: is it justified?

23 distinct (category, difficulty) cells across 92 tasks; cell sizes range 1-6 tasks, median 4. Only 18/23 cells have >= 3 tasks — a rule for the rest would be fit to 1-2 data points, indistinguishable from noise. **Not run as a strategy below** — combining two categorical axes fragments this dataset below the size where a rule means anything; category alone already uses the stronger, better-supported signal.

## Phase 2 — strategy comparison (real per-task data, no averages substituted)

| strategy | accuracy | correct | % on 20b | % on 120b | nominal cost | cost vs 20b | cost vs 120b | avg latency | latency vs 20b | latency vs 120b |
|---|---|---|---|---|---|---|---|---|---|---|
| A. Always 20b | 88.0% | 81/92 | 100.0% | 0.0% | $0.008108 | 1.00x | 0.54x | 646ms | 1.00x | 0.70x |
| B. Always 120b | 90.2% | 83/92 | 0.0% | 100.0% | $0.015020 | 1.85x | 1.00x | 927ms | 1.44x | 1.00x |
| C. Perfect oracle | 93.5% | 86/92 | 94.6% | 5.4% | $0.008187 | 1.01x | 0.55x | 655ms | 1.01x | 0.71x |
| D. Category-aware (full) | 91.3% | 84/92 | 79.3% | 20.7% | $0.008573 | 1.06x | 0.57x | 682ms | 1.06x | 0.74x |
| D2. Summarization-only override | 90.2% | 83/92 | 93.5% | 6.5% | $0.008193 | 1.01x | 0.55x | 651ms | 1.01x | 0.70x |
| E. Difficulty-aware | 90.2% | 83/92 | 32.6% | 67.4% | $0.012452 | 1.54x | 0.83x | 802ms | 1.24x | 0.86x |

**Actual billed cost for every strategy above: $0.00** — Groq free tier, no payment method on the account. The nominal_cost figures are notional (registry per-1k pricing x real token counts actually used by whichever model each strategy picked).

## Phase 3 — data leakage and generalization

The category rule above (Strategy D, 91.3% accuracy) was **derived from and evaluated on the identical 92 tasks — this is an IN-SAMPLE result and must not be read as evidence it generalizes.** A rule built by asking "which model wins each category on this exact data" is guaranteed to fit this exact data at least as well as either always-X baseline; the open question is whether the category→model assignment reflects a real, stable property of the models, or noise in a small sample.

**Why a conventional train/test split isn't the right tool here:** the entire routing opportunity is defined by just 8 disagreement tasks out of 92. A held-out test split (e.g. 80/20) would put roughly 1-2 disagreement tasks in the test set — not enough to distinguish "the rule generalizes" from "the rule got lucky/unlucky on the 1 task that mattered." Forcing an ML-style split here would produce a number that looks rigorous but measures almost nothing.

**Leave-one-out cross-validation (LOOCV) on the category rule**, chosen because it is the standard, most defensible approach for a dataset this small — it holds out exactly one task at a time (no leakage: that task's own label never informs the rule used to predict it), while still using every other task to build the rule each time, which a fixed train/test split can't afford to do here. Result: **81/92 = 88.0% LOOCV accuracy**, versus 91.3% in-sample — a +3.3% drop when the rule can't see the task it's predicting.

**This LOOCV accuracy is EXACTLY 88.0% — identical to always-20b's raw accuracy.** That is not a coincidence in the reassuring sense: traced per-task, the summarization signal genuinely survives LOOCV (5/6 correct held-out, matching the in-sample count exactly — every time a summarization task is excluded, the remaining 5 summarization tasks still clearly favor 120b), but that gain is exactly canceled by the category rule getting WORSE than always-20b on extraction: with extraction tied 76.9%/76.9% in-sample (defaulting to 20b), excluding either of extraction's two 20b-favoring disagreement tasks (extraction-002, extraction-005) from training flips the remaining data's tie toward 120b — so LOOCV predicts 120b for the exact two tasks where 20b was actually right, losing both. **Honest conclusion: the category rule's in-sample +3.3pt edge over always-20b does not survive out-of-fold testing at this sample size** — the summarization-specific signal is real and holds up, but the rule as a whole (including its razor-thin, easily-flipped tie-breaks in extraction and classification) does not yet demonstrate it generalizes beyond this exact dataset.

**Retesting with the narrower rule** ("summarization → 120b, everything else → 20b", D2) that drops the fragile classification/extraction tie-breaks entirely: **83/92 = 90.2% LOOCV accuracy — IDENTICAL to its own in-sample accuracy (90.2%)**. This is not a coincidence: the non-summarization branch is a hardcoded constant with zero free parameters (cannot overfit by construction), and the summarization branch's own leave-one-out folds all agree with each other (dropping either summarization disagreement task still leaves the remaining summarization data clearly favoring 120b). **This narrower rule is the one with genuine, demonstrated (not just claimed) out-of-fold validity** — it matches always-120b's 90.2% accuracy while sending only 6.5% of requests to 120b, and that number holds up under honest testing, unlike the full category rule's number.

## Phase 4 — disagreement analysis (8 tasks)

| task_id | category | difficulty | winner | 20b latency | 120b latency |
|---|---|---|---|---|---|
| classification-012 | classification | hard | 120b | 444ms | 596ms |
| extraction-002 | extraction | medium | 20b | 478ms | 356ms |
| extraction-005 | extraction | hard | 20b | 1055ms | 737ms |
| extraction-008 | extraction | easy | 120b | 318ms | 638ms |
| extraction-012 | extraction | medium | 120b | 409ms | 726ms |
| math-011 | math | hard | 20b | 547ms | 562ms |
| summarization-007 | summarization | medium | 120b | 553ms | 554ms |
| summarization-010 | summarization | hard | 120b | 634ms | 671ms |

Category concentration of wins (observable before seeing any answer — category and difficulty are task metadata, not derived from correctness):

- **classification**: 1 disagreement(s), 1 favor 120b, 0 favor 20b
- **extraction**: 4 disagreement(s), 2 favor 120b, 2 favor 20b
- **math**: 1 disagreement(s), 0 favor 120b, 1 favor 20b
- **summarization**: 2 disagreement(s), 2 favor 120b, 0 favor 20b

2/8 of all disagreements are 120b wins on summarization specifically. The remaining disagreements (extraction x3, math x1, classification x1) split 3-favor-20b vs 2-favor-120b — closer to noise than pattern at this sample size. **Verdict: summarization is the one category with a systematic, predictable-before-the-fact signal (120b wins there); the rest of the disagreement set is too small and mixed to call systematic** — which is exactly what the category rule above already encodes (it assigns summarization to 120b and defaults everything else to 20b in every category except one, since only summarization's within-category gap was large enough to flip the assignment).

## Phase 5 — best simple baseline

Not the highest in-sample scorer (that's D at 91.3%, but its LOOCV accuracy collapses to 88.0% — no better than always-20b). **D2. Summarization-only override** (90.2% in-sample, and — uniquely among the rules tested — 90.2% under LOOCV, i.e. no measured generalization gap) is the recommended baseline: simple enough to state in one sentence ("route summarization to 120b, everything else to 20b"), interviewable without a slide, and the only rule here whose out-of-sample performance was actually checked rather than assumed.

- vs always-20b: +2.2% accuracy, 1.01x nominal cost, 1.01x latency
- vs always-120b: +0.0% accuracy, 0.55x nominal cost (45.5% cost reduction), 0.70x latency (29.8% latency reduction)
- vs oracle: +3.3% accuracy short of the 93.5% ceiling, capturing 40% of the total available gap between always-20b and the oracle
- routes only 6.5% of requests to 120b (vs 100% for always-120b), while matching or approaching its accuracy

## Phase 6 — V3 decision inputs

1. **Does routing already provide useful value with only two Groq models?** Yes — D2. Summarization-only override reaches 90.2%, within 3.3% of the 93.5% oracle ceiling, using a one-line rule.
2. **Does the rule-based router match or beat always-120b?** Yes — 90.2% vs 90.2% (+0.0%).
3. **How much 120b usage can be avoided?** 93.5% of requests avoid 120b entirely (86/92 tasks), cutting nominal cost to 54.5% of always-120b's and latency to 70.2%.
4. **Quality tradeoff vs oracle?** 3.3% (3 task(s): the oracle also correctly routes the 6 non-summarization disagreement tasks, which no rule tested here — including D2 — can distinguish from noise at this sample size).
5. **Is there enough disagreement data to justify learned routing?** Not yet demonstrated — only 8 disagreement tasks total, and the one rule that passed LOOCV (D2, 90.2%) captures its entire gain from a single observable bit ("is this summarization") — it does not use the other 6 disagreement tasks at all, and LOOCV showed the fuller rule that tried to use them (D) does not generalize. A learned router would need to find real, generalizing structure in those remaining 6 tasks specifically - unproven with this little data, and the training-data-size problem that sank V3 twice before hasn't gone away.
6. **What would a learned router have to beat to be worthwhile?** Not always-20b or always-120b (the old baseline) - **D2. Summarization-only override at 90.2% (90.2% LOOCV-validated, not just in-sample), 6.5% 120b usage, 0.55x always-120b's nominal cost**. This is the new bar V3 must clear to justify its added complexity, and it must clear it under the same out-of-fold discipline, not just in-sample accuracy.

## Phase 7 — third model (Qwen) decision

Not run. The simple-routing result changes the question a third model would need to answer: the 20b/120b gap is now mostly explained by one category (summarization), not general capability. Before adding Qwen, the sharper question is whether it adds capability specifically where **both current models fail together** (6 tasks: classification-010, extraction-004, math-005, math-013, reasoning-003, summarization-013) - that's where a third model could expand the oracle ceiling itself, not just get closer to an already-known 93.5%. Recommend still holding Qwen until that specific question is worth asking, and running it only against those both-fail tasks plus the existing 92-task auto-gradeable set if approved - not all 104.

