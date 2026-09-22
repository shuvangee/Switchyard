from app.evaluation.validation import validate_response
from app.models.enums import TaskCategory, ValidationStatus


def test_math_passes_when_response_matches_computed_answer():
    outcome = validate_response(TaskCategory.MATH, "What is 17 * 6?", "102")
    assert outcome.status == ValidationStatus.PASSED


def test_math_fails_when_response_does_not_match():
    outcome = validate_response(TaskCategory.MATH, "What is 17 * 6?", "99")
    assert outcome.status == ValidationStatus.FAILED


def test_math_catches_the_actual_v1_failure_case():
    """This is the literal prompt that misrouted in V1 and got answer "23"
    from mock-fast-v1 (it ignores the leading minus sign). Validation must
    independently compute the correct answer (7) and flag the mismatch.
    """
    outcome = validate_response(TaskCategory.MATH, "What is -8 + 15?", "23")
    assert outcome.status == ValidationStatus.FAILED
    assert "7" in outcome.detail


def test_math_not_validated_without_computable_expression():
    outcome = validate_response(TaskCategory.MATH, "Explain the concept of zero.", "anything")
    assert outcome.status == ValidationStatus.NOT_VALIDATED


def test_classification_passes_for_allowed_label():
    prompt = "Classify sentiment. Respond with exactly one of: positive, negative, neutral."
    outcome = validate_response(TaskCategory.CLASSIFICATION, prompt, "positive")
    assert outcome.status == ValidationStatus.PASSED


def test_classification_fails_for_disallowed_response():
    prompt = "Classify sentiment. Respond with exactly one of: positive, negative, neutral."
    outcome = validate_response(TaskCategory.CLASSIFICATION, prompt, "somewhat mixed")
    assert outcome.status == ValidationStatus.FAILED


def test_classification_catches_the_actual_v1_failure_case():
    """The V1 Playground prompt that got a generic fallback string instead
    of a label ("Classify... as positive, negative, or neutral" doesn't
    match the "one of:" pattern mock.py looks for, so no label list was
    even extractable by the mock — but if a response is returned, it still
    must be checked against label list if present).
    """
    prompt = "Classify the sentiment of this review as positive, negative, or neutral."
    outcome = validate_response(TaskCategory.CLASSIFICATION, prompt, "[mock:basic] Response to prompt: x")
    # no "one of:" phrasing in this prompt -> nothing to check against
    assert outcome.status == ValidationStatus.NOT_VALIDATED


def test_structured_output_passes_for_valid_json():
    outcome = validate_response(TaskCategory.STRUCTURED_OUTPUT, "return json", '{"a": 1}')
    assert outcome.status == ValidationStatus.PASSED


def test_structured_output_fails_for_malformed_json():
    outcome = validate_response(TaskCategory.STRUCTURED_OUTPUT, "return json", '{"a": 1')
    assert outcome.status == ValidationStatus.FAILED


def test_extraction_passes_for_well_formed_email():
    prompt = "Extract the email from: reply to: alice@example.com"
    outcome = validate_response(TaskCategory.EXTRACTION, prompt, "alice@example.com")
    assert outcome.status == ValidationStatus.PASSED


def test_extraction_fails_for_malformed_email():
    prompt = "Extract the email from: reply to: alice@example.com"
    outcome = validate_response(TaskCategory.EXTRACTION, prompt, "not an email")
    assert outcome.status == ValidationStatus.FAILED


def test_extraction_not_validated_for_non_email_prompt():
    outcome = validate_response(TaskCategory.EXTRACTION, "Extract the phone number.", "555-1234")
    assert outcome.status == ValidationStatus.NOT_VALIDATED


def test_unscored_categories_are_never_validated():
    for category in (
        TaskCategory.SUMMARIZATION,
        TaskCategory.REASONING,
        TaskCategory.CODING,
        TaskCategory.DEBUGGING,
    ):
        outcome = validate_response(category, "anything", "anything")
        assert outcome.status == ValidationStatus.NOT_VALIDATED
