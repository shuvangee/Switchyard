from app.models.enums import TaskCategory, TaskDifficulty
from app.routing.analyzer import analyze_request


def test_explicit_category_hint_is_used_and_labeled_explicit():
    analysis = analyze_request("some arbitrary prompt", category_hint=TaskCategory.CODING)
    assert analysis.category == TaskCategory.CODING
    assert analysis.category_source == "explicit"


def test_math_detected_via_pattern():
    analysis = analyze_request("What is 17 * 6?")
    assert analysis.category == TaskCategory.MATH
    assert analysis.category_source == "heuristic"


def test_structured_output_keyword_detected():
    analysis = analyze_request('Return a JSON object with keys "name" and "age".')
    assert analysis.category == TaskCategory.STRUCTURED_OUTPUT
    assert analysis.structured_output_required is True


def test_classification_keyword_detected():
    analysis = analyze_request("Classify the sentiment of this review as positive or negative.")
    assert analysis.category == TaskCategory.CLASSIFICATION


def test_summarization_keyword_detected():
    analysis = analyze_request("Summarize the following article in one sentence.")
    assert analysis.category == TaskCategory.SUMMARIZATION


def test_debugging_keyword_detected():
    analysis = analyze_request("There is a bug in this function, please debug it.")
    assert analysis.category == TaskCategory.DEBUGGING


def test_coding_keyword_detected():
    analysis = analyze_request("Write a Python function that reverses a string.")
    assert analysis.category == TaskCategory.CODING


def test_extraction_keyword_detected():
    analysis = analyze_request("Extract the phone number from this text.")
    assert analysis.category == TaskCategory.EXTRACTION


def test_unrecognized_prompt_defaults_to_reasoning_not_a_false_positive():
    analysis = analyze_request("Why might a distributed system experience clock drift?")
    assert analysis.category == TaskCategory.REASONING


def test_difficulty_thresholds():
    easy = analyze_request("Short prompt.")
    medium = analyze_request(" ".join(["word"] * 30))
    hard = analyze_request(" ".join(["word"] * 90))
    assert easy.difficulty == TaskDifficulty.EASY
    assert medium.difficulty == TaskDifficulty.MEDIUM
    assert hard.difficulty == TaskDifficulty.HARD


def test_structured_output_not_required_by_default():
    analysis = analyze_request("What is 2 + 2?")
    assert analysis.structured_output_required is False


def test_token_estimate_is_positive_and_scales_with_length():
    short = analyze_request("Hi.")
    long = analyze_request(" ".join(["word"] * 50))
    assert short.estimated_input_tokens > 0
    assert long.estimated_input_tokens > short.estimated_input_tokens
