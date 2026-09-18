"""Structured trace events recorded for every routed request.

System-level events only — what the pipeline actually did and when, never
model reasoning or chain-of-thought. See docs/case-study/DECISIONS.md.
"""

from dataclasses import asdict, dataclass
from typing import Any

from app.core.time import utcnow


@dataclass(frozen=True)
class TraceEvent:
    event_type: str
    detail: str
    timestamp: str

    @classmethod
    def now(cls, event_type: str, detail: str) -> "TraceEvent":
        return cls(event_type=event_type, detail=detail, timestamp=utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
