"""Evaluation outcome type shared by all evaluation strategies."""

from dataclasses import dataclass

from app.models.enums import EvaluationStatus


@dataclass(frozen=True)
class EvaluationOutcome:
    status: EvaluationStatus
    detail: str | None = None
