"""Feature encoding for the learned router.

Small, fixed feature set — deliberately not "every possible feature."
Included: category and difficulty (the same two signals V1's rules are
built on, so a learned router is a fair comparison against them),
structured_output_required (cheap, direct signal already computed by the
analyzer), and estimated_input_tokens (the one continuous signal
available). Excluded: embeddings (unjustified at N=24 — nowhere near
enough data to fit a useful embedding-based model, and it would add a
real inference-time cost/latency for no evidenced benefit yet) and
historical per-model performance (would need a real, sizeable request
history to be anything but the same 24 rows restated).
"""

from dataclasses import dataclass

import numpy as np

from app.models.enums import TaskCategory, TaskDifficulty
from app.routing.analyzer import RequestAnalysis

_CATEGORIES = [c.value for c in TaskCategory]
_DIFFICULTY_ORDER = {TaskDifficulty.EASY: 0, TaskDifficulty.MEDIUM: 1, TaskDifficulty.HARD: 2}

FEATURE_NAMES = [f"category={c}" for c in _CATEGORIES] + [
    "difficulty_ordinal",
    "structured_output_required",
    "estimated_input_tokens",
]


@dataclass(frozen=True)
class EncodedFeatures:
    names: list[str]
    matrix: np.ndarray  # shape (n_rows, len(FEATURE_NAMES))


def encode(analyses: list[RequestAnalysis]) -> EncodedFeatures:
    rows = []
    for analysis in analyses:
        category_one_hot = [1.0 if c == analysis.category.value else 0.0 for c in _CATEGORIES]
        row = category_one_hot + [
            float(_DIFFICULTY_ORDER[analysis.difficulty]),
            1.0 if analysis.structured_output_required else 0.0,
            float(analysis.estimated_input_tokens),
        ]
        rows.append(row)
    return EncodedFeatures(names=FEATURE_NAMES, matrix=np.array(rows, dtype=float))
