"""Shared enums for benchmark tasks, evaluation, and execution outcomes."""

from enum import Enum


class TaskCategory(str, Enum):
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    MATH = "math"
    REASONING = "reasoning"
    CODING = "coding"
    DEBUGGING = "debugging"
    STRUCTURED_OUTPUT = "structured_output"


class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EvaluationType(str, Enum):
    EXACT_MATCH = "exact_match"
    CLASSIFICATION_LABEL = "classification_label"
    VALID_JSON = "valid_json"
    MANUAL = "manual"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class EvaluationStatus(str, Enum):
    NOT_EVALUATED = "not_evaluated"
    CORRECT = "correct"
    INCORRECT = "incorrect"


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"


class ValidationStatus(str, Enum):
    """Outcome of validating a *live* routed response (V2). Distinct from
    EvaluationStatus, which grades a benchmark task against a pre-authored
    expected_output — validation has no ground truth to compare against,
    only structural/content checks inferred from the request itself.
    """

    NOT_VALIDATED = "not_validated"  # no applicable automated check
    PASSED = "passed"
    FAILED = "failed"


class ConfidenceLevel(str, Enum):
    """A heuristic label on the router's own analysis, not a statistically
    calibrated probability. See docs/case-study/DECISIONS.md.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
