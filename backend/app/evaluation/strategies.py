"""Evaluation strategies for V0.

Each strategy answers one of three things: the response was not evaluated
at all (evaluation_type is manual, or there is nothing to compare against),
it was evaluated and matched, or it was evaluated and did not match. Those
are represented as distinct EvaluationStatus values so "not evaluated" and
"failed evaluation" are never confused with each other.
"""

import json

from app.evaluation.base import EvaluationOutcome
from app.models.enums import EvaluationStatus, EvaluationType


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def evaluate_exact_match(response: str, expected_output: str | None) -> EvaluationOutcome:
    if expected_output is None:
        return EvaluationOutcome(EvaluationStatus.NOT_EVALUATED, "no expected_output configured")
    if _normalize(response) == _normalize(expected_output):
        return EvaluationOutcome(EvaluationStatus.CORRECT)
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
