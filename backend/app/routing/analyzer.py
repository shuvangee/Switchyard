"""Request analyzer: a transparent, heuristic first pass over a raw prompt.

Everything here is a cheap proxy, not a validated classifier — word count
as a difficulty signal, keyword/regex matching as a category guess. This
is deliberate: V1 is a simple, explainable baseline, and pretending these
heuristics are more accurate than they are would undermine the one thing
that makes a rule-based router worth building (you can see exactly why it
did what it did). See docs/case-study/DECISIONS.md for the reasoning.
"""

import re
from dataclasses import dataclass

from app.models.enums import TaskCategory, TaskDifficulty


@dataclass(frozen=True)
class RequestAnalysis:
    category: TaskCategory
    category_source: str  # "explicit" (caller specified it) | "heuristic" (guessed)
    difficulty: TaskDifficulty
    structured_output_required: bool
    estimated_input_tokens: int


_MATH_PATTERN = re.compile(r"-?\d+(?:\.\d+)?\s*[+\-*/]\s*-?\d+(?:\.\d+)?")

# Checked in this order; first match wins. Category-defining keywords only
# — deliberately short lists, not an attempt at real NLP classification.
_CATEGORY_KEYWORDS: list[tuple[TaskCategory, tuple[str, ...]]] = [
    (TaskCategory.STRUCTURED_OUTPUT, ("json", "schema", "structured output")),
    (TaskCategory.CLASSIFICATION, ("classify", "classification", "sentiment", "categorize", "label")),
    (TaskCategory.SUMMARIZATION, ("summarize", "summary", "tl;dr", "tldr")),
    (TaskCategory.DEBUGGING, ("debug", "bug", "wrong result", "doesn't work", "not working", "fix the")),
    (TaskCategory.CODING, ("write a function", "write a python", "implement", "def ", "class ")),
    (TaskCategory.EXTRACTION, ("extract", "pull out", "find the email", "find the address")),
]

_EASY_WORD_LIMIT = 20
_MEDIUM_WORD_LIMIT = 60


def _guess_category(prompt: str) -> TaskCategory:
    if _MATH_PATTERN.search(prompt):
        return TaskCategory.MATH
    lowered = prompt.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return category
    # No stronger signal found. Open-ended prompts default to "reasoning"
    # rather than an artificially confident guess at a narrower category.
    return TaskCategory.REASONING


def _estimate_difficulty(prompt: str) -> TaskDifficulty:
    word_count = len(prompt.split())
    if word_count <= _EASY_WORD_LIMIT:
        return TaskDifficulty.EASY
    if word_count <= _MEDIUM_WORD_LIMIT:
        return TaskDifficulty.MEDIUM
    return TaskDifficulty.HARD


def _detect_structured_output(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(keyword in lowered for keyword in ("json", "schema", "structured output"))


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text.split()) * 1.3))


def analyze_request(prompt: str, category_hint: TaskCategory | None = None) -> RequestAnalysis:
    if category_hint is not None:
        category = category_hint
        category_source = "explicit"
    else:
        category = _guess_category(prompt)
        category_source = "heuristic"

    return RequestAnalysis(
        category=category,
        category_source=category_source,
        difficulty=_estimate_difficulty(prompt),
        structured_output_required=_detect_structured_output(prompt),
        estimated_input_tokens=_estimate_tokens(prompt),
    )
