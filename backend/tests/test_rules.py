from itertools import product

from app.models.enums import TaskCategory, TaskDifficulty
from app.routing.analyzer import RequestAnalysis
from app.routing.rules import DEFAULT_RULES


def _analysis(category: TaskCategory, difficulty: TaskDifficulty) -> RequestAnalysis:
    return RequestAnalysis(
        category=category,
        category_source="explicit",
        difficulty=difficulty,
        structured_output_required=False,
        estimated_input_tokens=10,
    )


def test_every_rule_has_a_nonempty_rationale():
    for rule in DEFAULT_RULES:
        assert rule.rationale.strip() != ""


def test_easy_deterministic_categories_route_to_fast():
    for category in (
        TaskCategory.EXTRACTION,
        TaskCategory.CLASSIFICATION,
        TaskCategory.MATH,
        TaskCategory.STRUCTURED_OUTPUT,
    ):
        analysis = _analysis(category, TaskDifficulty.EASY)
        matched = next(rule for rule in DEFAULT_RULES if rule.matches(analysis))
        assert matched.model_id == "mock-fast-v1"


def test_harder_deterministic_categories_route_to_accurate():
    for category in (
        TaskCategory.EXTRACTION,
        TaskCategory.CLASSIFICATION,
        TaskCategory.MATH,
        TaskCategory.STRUCTURED_OUTPUT,
    ):
        for difficulty in (TaskDifficulty.MEDIUM, TaskDifficulty.HARD):
            analysis = _analysis(category, difficulty)
            matched = next(rule for rule in DEFAULT_RULES if rule.matches(analysis))
            assert matched.model_id == "mock-accurate-v1"


def test_unscored_categories_always_route_to_accurate_regardless_of_difficulty():
    for category in (
        TaskCategory.SUMMARIZATION,
        TaskCategory.REASONING,
        TaskCategory.CODING,
        TaskCategory.DEBUGGING,
    ):
        for difficulty in TaskDifficulty:
            analysis = _analysis(category, difficulty)
            matched = next(rule for rule in DEFAULT_RULES if rule.matches(analysis))
            assert matched.model_id == "mock-accurate-v1"


def test_default_rules_cover_every_category_and_difficulty_combination():
    """No gap should exist that would fall through to the DEFAULT_MODEL_ID
    safety net under normal operation — every (category, difficulty) pair
    should match at least one configured rule.
    """
    for category, difficulty in product(TaskCategory, TaskDifficulty):
        analysis = _analysis(category, difficulty)
        assert any(rule.matches(analysis) for rule in DEFAULT_RULES), (
            f"no rule matches category={category}, difficulty={difficulty}"
        )
