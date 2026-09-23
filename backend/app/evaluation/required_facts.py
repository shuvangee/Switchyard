"""Zero-cost deterministic grader for summarization tasks: checks whether
a response mentions every fact its rubric requires, as a normalized
substring match (case-insensitive, whitespace-collapsed - same
normalization exact_match already uses).

NOT wired into EvaluationType/evaluate() - deliberately standalone, same
posture as backend/app/evaluation/sandbox.py for coding/debugging. Each
task's evaluation_type in benchmarks/tasks/*.json stays "manual"; this
is applied to evaluation_status via scripts/apply_summarization_grading_
results.py, once real response text exists.

WHY THIS METHOD, AND ITS REAL LIMIT: full comparison of approaches is in
docs/case-study/DECISIONS.md (2026-09-23). The short version: presence
of the required facts does not verify good prose, or that the response
doesn't ALSO include a fabricated or contradictory claim alongside the
correct ones, or - critically - that multiple facts are correctly
ATTRIBUTED to the right thing when a task's whole point is not
conflating two things (see summarization-009/012's exclusion below).
This is why only 6 of 13 summarization tasks are graded this way; the
other 7 either have no crisp fact-level rubric to check, have a
deliberately soft rubric ("ideally"), or are specifically testing
attribution/conflation, which presence-checking cannot verify.
"""

import re

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip().lower())


def check_required_facts(response: str, required_facts: list[str | list[str]]) -> tuple[bool, list]:
    """Each entry in required_facts is either a single required substring,
    or a list of acceptable alternatives (e.g. ["8s", "8 seconds"] - any
    one counts as present, to absorb reasonable phrasing/formatting
    variance without weakening what's actually required).

    Returns (all_present, missing_facts) - missing_facts lists whichever
    entries had none of their alternatives found, for a readable
    evaluation_detail message.
    """
    normalized_response = _normalize(response)
    missing: list = []
    for fact in required_facts:
        alternatives = fact if isinstance(fact, list) else [fact]
        if not any(_normalize(alt) in normalized_response for alt in alternatives):
            missing.append(fact)
    return (len(missing) == 0, missing)
