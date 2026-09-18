from app.evaluation.strategies import evaluate
from app.models.enums import EvaluationStatus, EvaluationType


def test_exact_match_correct():
    outcome = evaluate(EvaluationType.EXACT_MATCH, "102", "102")
    assert outcome.status == EvaluationStatus.CORRECT


def test_exact_match_incorrect():
    outcome = evaluate(EvaluationType.EXACT_MATCH, "103", "102")
    assert outcome.status == EvaluationStatus.INCORRECT


def test_exact_match_ignores_surrounding_whitespace_and_case():
    outcome = evaluate(EvaluationType.EXACT_MATCH, "  Hello World  ", "hello world")
    assert outcome.status == EvaluationStatus.CORRECT


def test_exact_match_not_evaluated_without_expected_output():
    outcome = evaluate(EvaluationType.EXACT_MATCH, "anything", None)
    assert outcome.status == EvaluationStatus.NOT_EVALUATED


def test_classification_label_correct_and_incorrect():
    assert evaluate(EvaluationType.CLASSIFICATION_LABEL, "positive", "positive").status == (
        EvaluationStatus.CORRECT
    )
    assert evaluate(EvaluationType.CLASSIFICATION_LABEL, "negative", "positive").status == (
        EvaluationStatus.INCORRECT
    )


def test_valid_json_incorrect_when_not_json():
    outcome = evaluate(EvaluationType.VALID_JSON, "not json at all", None)
    assert outcome.status == EvaluationStatus.INCORRECT


def test_valid_json_correct_with_no_expected_schema():
    outcome = evaluate(EvaluationType.VALID_JSON, '{"a": 1}', None)
    assert outcome.status == EvaluationStatus.CORRECT


def test_valid_json_correct_when_keys_match_expected():
    outcome = evaluate(EvaluationType.VALID_JSON, '{"name": "John", "age": 30}', '{"name": "", "age": 0}')
    assert outcome.status == EvaluationStatus.CORRECT


def test_valid_json_incorrect_when_keys_missing():
    outcome = evaluate(EvaluationType.VALID_JSON, '{"name": "John"}', '{"name": "", "age": 0}')
    assert outcome.status == EvaluationStatus.INCORRECT
    assert "age" in outcome.detail


def test_manual_is_always_not_evaluated():
    outcome = evaluate(EvaluationType.MANUAL, "anything at all", "irrelevant")
    assert outcome.status == EvaluationStatus.NOT_EVALUATED


def test_not_evaluated_is_distinct_from_incorrect():
    # A manual task's response is never "wrong" — it's simply not graded.
    not_evaluated = evaluate(EvaluationType.MANUAL, "some response", None)
    incorrect = evaluate(EvaluationType.EXACT_MATCH, "wrong", "right")
    assert not_evaluated.status != incorrect.status
    assert not_evaluated.status == EvaluationStatus.NOT_EVALUATED
    assert incorrect.status == EvaluationStatus.INCORRECT
