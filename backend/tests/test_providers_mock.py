import pytest

from app.providers.base import ProviderError
from app.providers.mock import MockProvider


@pytest.fixture()
def provider() -> MockProvider:
    return MockProvider()


def test_unknown_model_id_raises(provider):
    with pytest.raises(ProviderError):
        provider.generate("not-a-real-model", "hello")


def test_math_single_operation_correct_for_both_profiles(provider):
    prompt = "What is 17 * 6?"
    fast = provider.generate("mock-fast-v1", prompt)
    accurate = provider.generate("mock-accurate-v1", prompt)
    assert fast.text == "102"
    assert accurate.text == "102"


def test_math_with_negative_number_only_capable_gets_right(provider):
    prompt = "What is -8 + 15?"
    fast = provider.generate("mock-fast-v1", prompt)
    accurate = provider.generate("mock-accurate-v1", prompt)
    # basic's regex ignores the leading minus sign and reads "8 + 15" = 23
    assert fast.text == "23"
    # capable correctly reads "-8 + 15" = 7
    assert accurate.text == "7"


def test_classification_keyword_signal_picks_matching_label(provider):
    prompt = (
        "Classify the sentiment of this review. "
        "Respond with exactly one of: positive, negative, neutral.\n"
        "Review: This product is absolutely great, I love it."
    )
    result = provider.generate("mock-accurate-v1", prompt)
    assert result.text == "positive"


def test_extraction_basic_takes_first_match_capable_uses_cue(provider):
    prompt = (
        "For general inquiries see distractor@example.com. "
        "For support, reply to: real-target@example.com."
    )
    fast = provider.generate("mock-fast-v1", prompt)
    accurate = provider.generate("mock-accurate-v1", prompt)
    assert fast.text == "distractor@example.com"
    assert accurate.text == "real-target@example.com"


def test_structured_output_produces_keys_from_prompt(provider):
    prompt = 'Return a JSON object with keys "name" and "age" for: John is 30 years old.'
    result = provider.generate("mock-accurate-v1", prompt)
    import json

    parsed = json.loads(result.text)
    assert parsed["name"] == "John"
    assert parsed["age"] == 30


def test_flaky_model_can_raise_provider_error():
    provider = MockProvider()
    # Search a small space of prompts for one that trips the flaky model's
    # deterministic ~25% error rate, proving the error path is reachable.
    found_error = False
    for i in range(50):
        try:
            provider.generate("mock-flaky-v1", f"prompt number {i}")
        except ProviderError:
            found_error = True
            break
    assert found_error


def test_same_input_is_fully_deterministic(provider):
    prompt = "What is 3 + 4?"
    first = provider.generate("mock-accurate-v1", prompt)
    second = provider.generate("mock-accurate-v1", prompt)
    assert first == second


def test_result_includes_synthetic_token_and_latency_fields(provider):
    result = provider.generate("mock-fast-v1", "Summarize: the quick brown fox.")
    assert result.input_tokens is not None and result.input_tokens > 0
    assert result.output_tokens is not None and result.output_tokens > 0
    assert result.latency_ms >= 0
