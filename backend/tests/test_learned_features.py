from app.models.enums import TaskCategory, TaskDifficulty
from app.routing.analyzer import RequestAnalysis
from app.routing.learned.features import FEATURE_NAMES, encode


def _analysis(category, difficulty, structured=False, tokens=10) -> RequestAnalysis:
    return RequestAnalysis(
        category=category,
        category_source="heuristic",
        difficulty=difficulty,
        structured_output_required=structured,
        estimated_input_tokens=tokens,
    )


def test_encode_shape_matches_feature_names():
    encoded = encode([_analysis(TaskCategory.MATH, TaskDifficulty.EASY)])
    assert encoded.names == FEATURE_NAMES
    assert encoded.matrix.shape == (1, len(FEATURE_NAMES))


def test_category_one_hot_is_exclusive():
    encoded = encode([_analysis(TaskCategory.MATH, TaskDifficulty.EASY)])
    category_columns = encoded.matrix[0][: len(FEATURE_NAMES) - 3]
    assert category_columns.sum() == 1.0
    math_index = FEATURE_NAMES.index("category=math")
    assert encoded.matrix[0][math_index] == 1.0


def test_difficulty_ordinal_increases_with_difficulty():
    easy = encode([_analysis(TaskCategory.MATH, TaskDifficulty.EASY)])
    hard = encode([_analysis(TaskCategory.MATH, TaskDifficulty.HARD)])
    idx = FEATURE_NAMES.index("difficulty_ordinal")
    assert easy.matrix[0][idx] < hard.matrix[0][idx]


def test_structured_output_flag_and_token_count_pass_through():
    encoded = encode([_analysis(TaskCategory.STRUCTURED_OUTPUT, TaskDifficulty.MEDIUM, structured=True, tokens=42)])
    structured_idx = FEATURE_NAMES.index("structured_output_required")
    tokens_idx = FEATURE_NAMES.index("estimated_input_tokens")
    assert encoded.matrix[0][structured_idx] == 1.0
    assert encoded.matrix[0][tokens_idx] == 42.0
