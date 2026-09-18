"""Validates a *live* routed response — no pre-authored expected_output
exists (unlike benchmark-task evaluation in strategies.py), so every check
here is a structural/content check inferred from the request itself.

Deliberately honest about its limits: most categories have no automated
check at all (NOT_VALIDATED), and even the categories that do are only
checked when the prompt happens to contain an extractable signal (a
computable expression, an explicit label list, something email-shaped).
"Do not pretend every open-ended request can be automatically proven
correct" — CLAUDE.md.
"""

import json
import re
from dataclasses import dataclass

from app.models.enums import TaskCategory, ValidationStatus


@dataclass(frozen=True)
class ValidationOutcome:
    status: ValidationStatus
    detail: str | None = None


# Deliberately a separate copy from providers/mock.py's math regex, even
# though it looks identical: that one defines how a fake model computes an
# answer; this one defines how we independently check one. Coupling them
# would make validation silently depend on mock-provider internals.
_MATH_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)")
_LABEL_LIST_PATTERN = re.compile(r"one of:\s*([^.\n]+)", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}")


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _apply_op(a: float, op: str, b: float) -> float:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b if b != 0 else float("nan")
    raise ValueError(f"unsupported operator: {op}")


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(round(value, 4))


def _validate_math(prompt: str, response: str) -> ValidationOutcome:
    match = _MATH_PATTERN.search(prompt)
    if not match:
        return ValidationOutcome(ValidationStatus.NOT_VALIDATED, "no computable expression found in prompt")
    expected = _format_number(_apply_op(float(match.group(1)), match.group(2), float(match.group(3))))
    if _normalize(response) == _normalize(expected):
        return ValidationOutcome(ValidationStatus.PASSED, f"matches independently computed {expected}")
    return ValidationOutcome(
        ValidationStatus.FAILED, f"independently computed {expected}, response was {response!r}"
    )


def _validate_classification(prompt: str, response: str) -> ValidationOutcome:
    label_match = _LABEL_LIST_PATTERN.search(prompt)
    if not label_match:
        return ValidationOutcome(ValidationStatus.NOT_VALIDATED, "no explicit label list found in prompt")
    labels = [label.strip().strip("\"'") for label in label_match.group(1).split(",")]
    labels = [label for label in labels if label]
    if not labels:
        return ValidationOutcome(ValidationStatus.NOT_VALIDATED, "label list was empty after parsing")
    if _normalize(response) in {_normalize(label) for label in labels}:
        return ValidationOutcome(ValidationStatus.PASSED, "response is one of the allowed labels")
    return ValidationOutcome(ValidationStatus.FAILED, f"expected one of {labels}, got {response!r}")


def _validate_structured_output(prompt: str, response: str) -> ValidationOutcome:
    try:
        json.loads(response)
    except json.JSONDecodeError as exc:
        return ValidationOutcome(ValidationStatus.FAILED, f"response is not valid JSON: {exc}")
    return ValidationOutcome(ValidationStatus.PASSED, "response is valid JSON")


def _validate_extraction(prompt: str, response: str) -> ValidationOutcome:
    if "email" not in prompt.lower() and not _EMAIL_PATTERN.search(prompt):
        return ValidationOutcome(
            ValidationStatus.NOT_VALIDATED, "extraction target not recognized (only email is checked)"
        )
    if _EMAIL_PATTERN.fullmatch(response.strip()):
        return ValidationOutcome(ValidationStatus.PASSED, "response is a well-formed email address")
    return ValidationOutcome(ValidationStatus.FAILED, f"response is not a well-formed email address: {response!r}")


_VALIDATORS = {
    TaskCategory.MATH: _validate_math,
    TaskCategory.CLASSIFICATION: _validate_classification,
    TaskCategory.STRUCTURED_OUTPUT: _validate_structured_output,
    TaskCategory.EXTRACTION: _validate_extraction,
}


def validate_response(category: TaskCategory, prompt: str, response: str) -> ValidationOutcome:
    """category here reuses TaskCategory (not EvaluationType, which only
    benchmark tasks have) — a freeform request has no author-assigned
    evaluation_type, so the category itself picks the validator.

    summarization/reasoning/coding/debugging have no automated check at
    all (no sandboxed code execution, no ground truth) — always
    NOT_VALIDATED, never a false PASSED/FAILED.
    """
    validator = _VALIDATORS.get(category)
    if validator is None:
        return ValidationOutcome(
            ValidationStatus.NOT_VALIDATED, f"no automated validator for category {category.value!r}"
        )
    return validator(prompt, response)
