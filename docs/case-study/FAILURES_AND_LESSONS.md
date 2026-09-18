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
