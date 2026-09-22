"""Evaluation strategies for V0.

Each strategy answers one of three things: the response was not evaluated
at all (evaluation_type is manual, or there is nothing to compare against),
it was evaluated and matched, or it was evaluated and did not match. Those
are represented as distinct EvaluationStatus values so "not evaluated" and
"failed evaluation" are never confused with each other.
"""

import json
import re

from app.evaluation.base import EvaluationOutcome
from app.models.enums import EvaluationStatus, EvaluationType

# Strips a leading/trailing markdown code fence, e.g. ```json ... ``` or ``` ... ```.
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _strip_code_fence(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text.strip())


def evaluate_exact_match(response: str, expected_output: str | None) -> EvaluationOutcome:
    if expected_output is None:
        return EvaluationOutcome(EvaluationStatus.NOT_EVALUATED, "no expected_output configured")
    normalized_response = _normalize(response)
    normalized_expected = _normalize(expected_output)
    if normalized_response == normalized_expected:
        return EvaluationOutcome(EvaluationStatus.CORRECT)
    # A real model restates the question or wraps the answer in a sentence
    # (e.g. "17 * 6 = **102**" for expected "102") — the mock provider this
    # strategy was written against never did that, so exact whole-string
    # equality alone missed a genuinely correct answer. Falls back to
    # requiring the expected value appear as its own token (word-bounded,
    # so expected "7" doesn't match inside "17") rather than anywhere the
    # substring happens to occur.
    if re.search(rf"\b{re.escape(normalized_expected)}\b", normalized_response):
        return EvaluationOutcome(
            EvaluationStatus.CORRECT,
            "expected value found as a distinct token in a longer response",
        )
    return EvaluationOutcome(
        EvaluationStatus.INCORRECT, f"expected {expected_output!r}, got {response!r}"
    )


def evaluate_classification_label(response: str, expected_output: str | None) -> EvaluationOutcome:
    if expected_output is None:
        return EvaluationOutcome(EvaluationStatus.NOT_EVALUATED, "no expected_output configured")
    if _normalize(response) == _normalize(expected_output):
        return EvaluationOutcome(EvaluationStatus.CORRECT)
    return EvaluationOutcome(
        EvaluationStatus.INCORRECT, f"expected label {expected_output!r}, got {response!r}"
    )


def evaluate_valid_json(response: str, expected_output: str | None) -> EvaluationOutcome:
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        # A real model commonly wraps JSON in a markdown code fence — the
        # mock provider never did, so this strategy only ever tried parsing
        # the raw string. Retry once with the fence stripped before giving
        # up; if that still doesn't parse, report the *original* error so
        # the message reflects what the model actually returned.
        try:
            parsed = json.loads(_strip_code_fence(response))
        except json.JSONDecodeError as exc:
            return EvaluationOutcome(EvaluationStatus.INCORRECT, f"response is not valid JSON: {exc}")

    if expected_output is None:
        return EvaluationOutcome(EvaluationStatus.CORRECT, "valid JSON (no schema to check against)")

    try:
        expected_parsed = json.loads(expected_output)
    except json.JSONDecodeError:
        return EvaluationOutcome(EvaluationStatus.CORRECT, "valid JSON (expected_output not parseable as JSON)")

    if not isinstance(expected_parsed, dict) or not isinstance(parsed, dict):
        return EvaluationOutcome(EvaluationStatus.CORRECT, "valid JSON (non-object expected_output, keys not checked)")

    missing = sorted(set(expected_parsed) - set(parsed))
    extra = sorted(set(parsed) - set(expected_parsed))
    if missing or extra:
        detail = f"missing keys {missing}, extra keys {extra}"
        return EvaluationOutcome(EvaluationStatus.INCORRECT, detail)
    return EvaluationOutcome(EvaluationStatus.CORRECT, "valid JSON with expected keys")


def evaluate_manual(response: str, expected_output: str | None) -> EvaluationOutcome:
    return EvaluationOutcome(EvaluationStatus.NOT_EVALUATED, "manual/unscored evaluation type")


_STRATEGIES = {
    EvaluationType.EXACT_MATCH: evaluate_exact_match,
    EvaluationType.CLASSIFICATION_LABEL: evaluate_classification_label,
    EvaluationType.VALID_JSON: evaluate_valid_json,
    EvaluationType.MANUAL: evaluate_manual,
}


def evaluate(
    evaluation_type: EvaluationType, response: str, expected_output: str | None
) -> EvaluationOutcome:
    strategy = _STRATEGIES[evaluation_type]
    return strategy(response, expected_output)
