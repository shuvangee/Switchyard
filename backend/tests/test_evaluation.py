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


def test_exact_match_correct_when_expected_value_is_a_token_in_a_longer_response():
    # Real model behavior found in the first Gemini experiment (2026-09-20):
    # restating the expression instead of answering with the bare value.
    outcome = evaluate(EvaluationType.EXACT_MATCH, "17 * 6 = **102**", "102")
    assert outcome.status == EvaluationStatus.CORRECT


def test_exact_match_does_not_match_expected_value_inside_a_longer_number():
    # "7" must not match inside "17" — token match, not raw substring.
    outcome = evaluate(EvaluationType.EXACT_MATCH, "the answer is 17", "7")
    assert outcome.status == EvaluationStatus.INCORRECT


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


def test_valid_json_correct_when_wrapped_in_markdown_code_fence():
    # Real model behavior found in the first Gemini experiment (2026-09-20):
    # wrapping JSON in a ```json ... ``` fence, which json.loads() alone
    # cannot parse even though the JSON inside is well-formed.
    fenced = '```json\n{"name": "John", "age": 30}\n```'
    outcome = evaluate(EvaluationType.VALID_JSON, fenced, '{"name": "", "age": 0}')
    assert outcome.status == EvaluationStatus.CORRECT


def test_valid_json_still_incorrect_when_fence_stripped_content_is_not_json():
    fenced = "```json\nnot actually json\n```"
    outcome = evaluate(EvaluationType.VALID_JSON, fenced, None)
    assert outcome.status == EvaluationStatus.INCORRECT


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
