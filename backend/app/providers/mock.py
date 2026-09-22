"""Mock provider: three deterministic, hash-seeded model profiles.

This exists so the whole benchmarking pipeline can be developed and tested
with zero API cost. It is a stand-in for a real model, not an attempt to
predict what one would say — everything here is honest about being
synthetic:

- Latency and token counts are synthetic approximations, not measurements
  of real inference.
- Response *content* is produced by small, genuinely-naive text processing
  on the visible prompt (regex arithmetic, a keyword sentiment lexicon,
  regex extraction, regex key-extraction for JSON) — it never has access
  to a task's `expected_output`. Correctness varies because these are real
  (if simple) heuristics that succeed or fail depending on prompt
  difficulty and profile "skill level," not because outcomes are
  hand-picked.
- All randomness is a deterministic hash of (model_id, prompt), so the
  same call always returns the same result and tests are reproducible.

The prompt-sniffing here (try math, then classification, then extraction,
then structured output, then a generic fallback) is tuned to this repo's
sample benchmark tasks under benchmarks/tasks/ — it is not a general NLP
system.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from app.providers.base import Provider, ProviderError, ProviderResult


@dataclass(frozen=True)
class MockProfile:
    simulated_latency_ms: tuple[float, float]
    error_rate: float
    skill_level: str  # "basic" | "capable"


_PROFILES: dict[str, MockProfile] = {
    "mock-fast-v1": MockProfile(simulated_latency_ms=(20.0, 120.0), error_rate=0.0, skill_level="basic"),
    "mock-accurate-v1": MockProfile(simulated_latency_ms=(250.0, 800.0), error_rate=0.0, skill_level="capable"),
    "mock-flaky-v1": MockProfile(simulated_latency_ms=(50.0, 300.0), error_rate=0.25, skill_level="basic"),
}


def _unit_interval(key: str) -> float:
    """Deterministic pseudo-random float in [0, 1) derived from `key`."""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


# "basic" only recognizes positive integers, so a negative sign or a
# decimal point derails it onto the wrong (but still plausible-looking)
# pair of operands — a realistic failure mode for a weaker model, not a
# crash. "capable" handles both correctly.
_BASIC_MATH_PATTERN = re.compile(r"(\d+)\s*([+\-*/])\s*(\d+)")
_CAPABLE_MATH_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)")


def _apply_op(a: float, op: str, b: float) -> float:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b if b != 0 else float("nan")
    raise ValueError(f"unsupported operator: {op}")


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(round(value, 4))


def _try_math(prompt: str, skill_level: str) -> str | None:
    pattern = _CAPABLE_MATH_PATTERN if skill_level == "capable" else _BASIC_MATH_PATTERN
    match = pattern.search(prompt)
    if not match:
        return None
    result = _apply_op(float(match.group(1)), match.group(2), float(match.group(3)))
    return _format_number(result)


_LABEL_LIST_PATTERN = re.compile(r"one of:\s*([^.\n]+)", re.IGNORECASE)

_BASIC_SENTIMENT_WORDS = {
    "positive": {"great", "love", "good"},
    "negative": {"bad", "hate", "terrible"},
}
_CAPABLE_SENTIMENT_WORDS = {
    "positive": {
        "great", "love", "good", "excellent", "amazing", "wonderful",
        "fantastic", "happy", "best", "enjoy", "impressed", "smooth",
    },
    "negative": {
        "bad", "hate", "terrible", "awful", "worst", "horrible",
        "disappointing", "poor", "sad", "broken", "frustrating", "slow",
    },
}


def _try_classification(prompt: str, skill_level: str) -> str | None:
    label_match = _LABEL_LIST_PATTERN.search(prompt)
    if not label_match:
        return None
    labels = [label.strip().strip("\"'") for label in label_match.group(1).split(",")]
    labels = [label for label in labels if label]
    if not labels:
        return None

    lexicon = _CAPABLE_SENTIMENT_WORDS if skill_level == "capable" else _BASIC_SENTIMENT_WORDS
    lowered = prompt.lower()
    scores = {label: 0 for label in labels}
    for label, words in lexicon.items():
        if label in scores:
            scores[label] = sum(1 for word in words if word in lowered)

    best_label = max(labels, key=lambda label: scores[label])
    if scores[best_label] == 0:
        if skill_level == "capable" and "neutral" in labels:
            return "neutral"
        return labels[0]
    return best_label


_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}")
_EMAIL_CUE_PATTERN = re.compile(
    r"(?:reply to|contact)[:\s]+([\w.+-]+@[\w-]+\.[a-zA-Z]{2,})", re.IGNORECASE
)


def _try_extraction(prompt: str, skill_level: str) -> str | None:
    if not _EMAIL_PATTERN.search(prompt):
        return None
    if skill_level == "capable":
        cue_match = _EMAIL_CUE_PATTERN.search(prompt)
        if cue_match:
            return cue_match.group(1)
    match = _EMAIL_PATTERN.search(prompt)
    return match.group(0) if match else None


_QUOTED_KEY_PATTERN = re.compile(r"[\"'](\w+)[\"']")
_DATA_SEGMENT_PATTERN = re.compile(r"for:\s*(.*)$", re.IGNORECASE | re.DOTALL)


def _data_segment(prompt: str) -> str:
    """The part of the prompt describing the actual data, by convention
    everything after "for:" — keeps instruction text (which often starts
    with its own capitalized word, e.g. "Return...") out of extraction.
    """
    match = _DATA_SEGMENT_PATTERN.search(prompt)
    return match.group(1) if match else prompt


def _try_structured_output(prompt: str, skill_level: str, seed: float) -> str | None:
    keys = _QUOTED_KEY_PATTERN.findall(prompt)
    if not keys:
        return None

    data = _data_segment(prompt)
    obj: dict[str, Any] = {}
    for key in keys:
        lowered_key = key.lower()
        if "name" in lowered_key:
            name_match = re.search(r"\b([A-Z][a-z]+)\b", data)
            obj[key] = name_match.group(1) if name_match else "unknown"
        elif any(token in lowered_key for token in ("age", "count", "number")):
            num_match = re.search(r"\b(\d+)\b", data)
            obj[key] = int(num_match.group(1)) if num_match else 0
        else:
            obj[key] = "value"

    text = json.dumps(obj)
    if skill_level == "basic" and seed < 0.3:
        # Simulate an occasional malformed response from the weaker profile.
        text = text[:-1]
    return text


def _fallback_response(prompt: str, skill_level: str) -> str:
    if skill_level == "capable":
        return (
            f"[mock:capable] Considered response addressing the prompt "
            f"({len(prompt)} chars): key points would be identified and "
            f"answered in a structured way."
        )
    return f"[mock:basic] Response to prompt: {prompt[:60]}"


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text.split()) * 1.3))


class MockProvider(Provider):
    name = "mock"

    def generate(self, model_id: str, prompt: str) -> ProviderResult:
        profile = _PROFILES.get(model_id)
        if profile is None:
            raise ProviderError(f"unknown mock model_id: {model_id!r}")

        error_seed = _unit_interval(f"error:{model_id}:{prompt}")
        if error_seed < profile.error_rate:
            raise ProviderError(f"mock provider {model_id!r} simulated a transient failure")

        latency_seed = _unit_interval(f"latency:{model_id}:{prompt}")
        lo, hi = profile.simulated_latency_ms
        latency_ms = lo + latency_seed * (hi - lo)

        content_seed = _unit_interval(f"content:{model_id}:{prompt}")
        text = (
            _try_math(prompt, profile.skill_level)
            or _try_classification(prompt, profile.skill_level)
            or _try_extraction(prompt, profile.skill_level)
            or _try_structured_output(prompt, profile.skill_level, content_seed)
            or _fallback_response(prompt, profile.skill_level)
        )

        return ProviderResult(
            text=text,
            input_tokens=_estimate_tokens(prompt),
            output_tokens=_estimate_tokens(text),
            latency_ms=latency_ms,
        )
