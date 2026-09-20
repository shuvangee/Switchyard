# Failures and lessons

Things that didn't work: approaches tried and abandoned, bugs that
revealed a wrong assumption, benchmarks that turned out to be measuring the
wrong thing. This is often the most interesting part of the case study in
an interview, and the easiest to lose if it isn't written down as it
happens.

## What belongs here

- What was tried.
- Why it didn't work (root cause, not just symptom).
- What changed as a result.

## Log

## 2026-09-18 — Greedy email regex swallowed trailing sentence punctuation

**What was tried:** The mock provider's extraction heuristic used
`[\w.+-]+@[\w-]+\.[\w.-]+` to pull an email address out of a prompt.

**Why it didn't work:** The trailing `[\w.-]+` is greedy and happily
consumes a sentence-ending period, so `"...reply to: alice@example.com."`
extracted `alice@example.com.` (with the period) instead of the email.
A test asserting the exact extracted string caught it immediately.

**What changed:** Tightened the TLD portion to `[a-zA-Z]{2,}` (letters
only), so the regex naturally stops before trailing punctuation. General
lesson: a "match everything email-shaped" regex needs an explicit,
narrower boundary at the end, not a permissive one — the failure mode is
silent (still looks like a plausible email) rather than a crash.

## 2026-09-18 — Name extraction matched the instruction sentence, not the data

**What was tried:** For structured-output prompts like `Return a JSON
object with keys "name" and "age" for: John is 30 years old.`, extracting
a "name" value via `\b([A-Z][a-z]+)\b` searched over the whole prompt.

**Why it didn't work:** "Return" — the first word of the instruction
sentence — is also capitalized, and regex search finds it before "John".

**What changed:** Introduced a convention (data always follows `for:` in
these prompts) and restricted the search to the substring after that
marker. General lesson: when a prompt mixes instruction text and data,
targeting a substring by a delimiting convention beats trying to write a
smarter pattern that guesses which capitalized word is "the real one."

## 2026-09-18 — "Chained math" didn't chain the way it looked like it would

**What was tried:** To make the "capable" mock profile handle a harder,
multi-step arithmetic prompt, the first design used `re.finditer` to find
every `number op number` match in the prompt and applied them in sequence
(so "10 + 5, then * 2" would resolve as `(10+5)*2`).

**Why it didn't work:** `finditer` only returns *non-overlapping* matches,
and once a match consumes a number, that number is gone from the string
for the next search. "10 + 5, then * 2" only contains one `number op
number` pattern at all ("10 + 5") — "then * 2" has no number *before* the
operator, so there was never a second match to chain. Both profiles
silently returned the same (single-operation) answer; a test that actually
asserted the two profiles differed caught this before it shipped.

**What changed:** Replaced "chaining multiple regex matches" with a
simpler, more robust distinction: the "basic" profile's regex only
recognizes positive integers, while "capable" also handles a leading minus
sign and decimals. A prompt like `-8 + 15` then genuinely produces
different (and differently *wrong*, for basic) answers, without depending
on a multi-match regex trick that only worked for the one example prompt
it was written against. General lesson: a "does the assertion I wrote
about my regex's behavior actually hold" test is worth writing before
trusting a regex trick to generalize past the one input you tried it on.

## 2026-09-18 — Test isolation required not using TestClient's context manager

**What was tried:** The natural way to test a FastAPI app end to end is
`with TestClient(app) as client: ...`, which runs the app's real
startup/shutdown lifespan.

**Why it would have been a problem:** `app.main`'s lifespan syncs
benchmark tasks and the model registry into the database built from
*production* `Settings` (`sqlite:///./switchyard.db` by default) — running
it during tests would create/modify a real file on disk, with behavior
depending on the test runner's current working directory.

**What changed:** API tests override the `get_db` dependency with a
session bound to an isolated in-memory database seeded directly in the
fixture, and construct `TestClient(app)` *without* the `with` block —
Starlette only sends lifespan events when the client is used as a context
manager, so the real lifespan (and the real engine it touches) never runs
during tests. Verified with a filesystem check after the full test suite
that no `.db` file was created outside of `:memory:`.

## 2026-09-18 — SQLAlchemy reserves `metadata` as a model attribute

**What was tried:** Naming a benchmark task's free-form JSON column
`metadata`, matching the field name used in the benchmark task schema.

**Why it didn't work:** SQLAlchemy's `DeclarativeBase` already defines
`metadata` as the class attribute holding the table registry
(`Base.metadata`) — a column named `metadata` on the model collides with
it.

**What changed:** Named the ORM column `task_metadata` and mapped it to
the API/schema field `metadata` explicitly in `BenchmarkTaskOut` rather
than relying on attribute-name matching. General lesson: `metadata` (and a
handful of other SQLAlchemy-reserved names) needs a different column name
at the ORM layer even when it's the most natural field name for the
domain/API.

## 2026-09-18 — Word-count difficulty estimation misroutes negative-number math

**What was tried:** V1's request analyzer estimates difficulty purely from
prompt word count (see `DECISIONS.md`). "What is -8 + 15?" is 5 words, so
it's estimated `easy` and routed to `mock-fast-v1` under the
easy-deterministic-to-fast rule.

**Why it didn't work:** `mock-fast-v1`'s "basic" math heuristic only
recognizes positive integers (this was already known from V0 — see the
"chained math" entry above); it reads "-8 + 15" as "8 + 15" and answers
`23`, not `7`. Word count has no relationship to *numeric* complexity, so
the one thing that actually determines whether this specific model gets
the answer right — a leading minus sign — is invisible to the difficulty
estimator entirely. Confirmed live: routing the identical arithmetic
problem with more words around it ("Please carefully work through this
arithmetic problem... what is negative eight plus fifteen, i.e. -8 + 15?")
crosses the word-count threshold into `medium`, correctly routes to
`mock-accurate-v1`, and gets `7` — the *only* reason it's now correct is
that the rephrasing happened to be longer, not that the router understood
anything about the math.

**What changed:** Nothing — documented deliberately rather than patched.
A quick fix (e.g. "math + contains a minus sign → hard") would just be
teaching the analyzer MockProvider's specific internals again, which
`DECISIONS.md` already rejected once for the same reason: it would stop
meaning anything the moment a real provider replaces the mock. This is a
real, load-bearing limitation of V1: an explainable rule-based router is
still only as good as the difficulty signal feeding it, and V1's signal is
genuinely weak. Recorded here as the concrete argument for V2 (confidence/
escalation, which can catch a wrong answer after the fact instead of
requiring a perfect prediction beforehand).

## 2026-09-18 — Mock classification heuristic doesn't generalize to Playground phrasing

**What was tried:** Routing a freeform Playground request — "Classify the
sentiment of this review as positive, negative, or neutral: I absolutely
love this, it is great." — through the router.

**Why it didn't work:** Routing itself was correct (category=
classification, difficulty=easy, model=mock-fast-v1, exactly per the
evidence-based rule). But the response was the generic fallback string
("[mock:basic] Response to prompt: ...") instead of an actual label,
because `MockProvider._try_classification` only recognizes the literal
phrase `"one of: X, Y, Z"` (matching how the V0 benchmark tasks are
worded) — "as positive, negative, or neutral" doesn't match that pattern,
so the classification heuristic silently declines and falls through.

**What changed:** Nothing, and this is a different kind of limitation than
the one above — worth distinguishing clearly. The *router* made a
perfectly reasonable, well-evidenced decision; the *mock provider's* own
naive heuristic just wasn't built to handle phrasing beyond the curated
benchmark set it was designed against (documented already in `mock.py`'s
module docstring). It's a preexisting, known constraint of the mock
surfacing in a new context (freeform input) rather than a new bug. Real
providers won't have this specific failure mode (they don't need
"one of:" phrasing to classify sentiment) — but it's a reminder that
Playground responses routed to the mock provider will generally look
worse on open-ended phrasing than the curated benchmark tasks do.

## 2026-09-20 — Three model ids before one actually worked

**What was tried:** Registered `gemini-2.0-flash` in the model registry
based on general knowledge of Gemini's model lineup, then tried to run
the 12-task real-provider experiment against it.

**Why it didn't work:** `404 Not Found`. A live call to Gemini's
`/v1beta/models` listing endpoint showed this key's account has no
`gemini-2.0-flash` at all — it isn't in the available model list. Picked
`gemini-2.5-flash` from that list instead (also cross-checked pricing via
web search, since `ai.google.dev` is blocked by this environment's
network policy) and tried again: also `404`, this time with an actual
Google error body explaining why — `"This model models/gemini-2.5-flash
is no longer available to new users. Please update your code to use
models/gemini-3.6-flash."` Registered `gemini-3.6-flash` and it worked.

**What changed:** Nothing structural — this is a lesson about external
dependency drift, not a code bug. Both failed attempts cost genuinely
$0.00 (a 404 happens before any token is generated or billed), so no
budget was wasted chasing the wrong name. General lesson: for a
fast-moving model API, don't trust a model id from training
knowledge or even a recent web search as ground truth — verify against a
live models-list call first, and when a real call 404s, read the error
body before guessing again; Google's own error named the exact
replacement model on the second attempt.

## 2026-09-20 — V0's evaluators undercount a real model's correctness

**What was tried:** Ran the 12 benchmark tasks for real against
`gemini-3.6-flash` (Switchyard's first real-provider experiment — see
`docs/case-study/EXPERIMENTS.md` for the full run). Of the 8 tasks with a
deterministic evaluator (`exact_match`/`valid_json`), only 3 were marked
`correct`.

**Why it didn't work:** Reading the actual response text for the other 5,
every one of them contains a substantively correct answer:
- `math-001`: `"17 * 6 = **102**"` (102 is correct) → marked `incorrect`.
- `math-002`: `"-8 + 15 = **7**"` (7 is correct) → marked `incorrect`.
- `extraction-002`: `"The correct contact email address is
  **real-target@example.com**."` (exactly the expected address) → marked
  `incorrect`.
- `structured_output-001`/`002`: valid JSON with exactly the right keys,
  wrapped in a ```` ```json ... ``` ```` markdown fence → marked
  `incorrect`.

`evaluate_exact_match` (`backend/app/evaluation/strategies.py`) requires
the *entire* normalized response to equal the expected string — it has no
tolerance for a real model restating the question or adding a sentence
around the answer. `evaluate_valid_json` calls `json.loads()` directly on
the raw response with no markdown-fence stripping, so a real model's
completely standard habit of wrapping code/JSON in a fence makes every
such response fail parsing outright, regardless of whether the JSON
inside is correct. Both strategies were written and tested exclusively
against `MockProvider`, which was deliberately built to emit bare,
unformatted answers (`"7"`, `{"name": "John", "age": 30}` with no fence)
— so this bug was invisible for the entire V0/V1/V2 mock-only evidence
base and only surfaced the moment a real, conversational model was used.

**What changed (fixed 2026-09-20, same day, in a separate deliberate pass —
not a same-session reflex patch):** Two targeted fixes to
`backend/app/evaluation/strategies.py`, scoped to exactly the two
confirmed root causes and nothing else:
- `evaluate_exact_match` now falls back to a **word-bounded token match**
  (`\bexpected\b` against the normalized response) when whole-string
  equality fails — so `"17 * 6 = **102**"` matches expected `"102"`, but
  expected `"7"` still correctly does *not* match inside `"17"` (verified
  with a dedicated regression test).
- `evaluate_valid_json` now retries once with a markdown code fence
  stripped (` ```json ... ``` `) before giving up on `json.loads()`.
- `evaluate_classification_label` and the JSON key-comparison logic were
  left untouched — step 1's diagnosis never implicated them.

**Verification (no new API calls):** Re-scored all 48 existing rows —
the 36 mock rows via `MockProvider` (a deterministic hash-seeded function
of `(model_id, prompt)`, so regenerating its output is a pure local
computation reproducing the original run's exact text, not a new call)
and the 12 Gemini rows via the actual raw response text already captured
during the real run. Script: `scripts/rescore_evaluator_fix.py`. Result:
**exactly the 5 diagnosed Gemini rows changed, all from `incorrect` to
`correct`; zero regressions** (no row that was `correct` under the old
evaluator became anything else). All 36 mock rows were unchanged — the
mock's bare output style was always compatible with the old, stricter
evaluator, which is itself confirmation of the root cause: the evaluator
was never wrong for mock-shaped text, only for real-model-shaped text.
Gemini's deterministically-scored tasks now read **8/8 correct**, matching
the manual review exactly.

**Why this matters more than the specific bug:** This directly confirms
the leakage/bias concern raised in the 2026-09-19 V3 data-readiness
review — that V0's only "quality" labels were a function of MockProvider's
specific output shape, not of real correctness. Now proven, not just
argued: the original raw automated score for the Gemini run (3/8 correct)
was not an honest measure of `gemini-3.6-flash`'s actual quality — it was
a measure of how closely a model's formatting habits happened to match
MockProvider's. Any future real-provider comparison built on
`evaluation_status` from before this fix would have silently made every
conversational real model look far worse than a terse one, regardless of
actual answer quality. Fixed now, before any such comparison was made.
