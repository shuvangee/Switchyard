"""Real provider adapter: Google's Gemini API (generateContent) over plain HTTP.

Uses `httpx` directly instead of a Google SDK, matching the OpenAI adapter's
approach — a thin adapter, not a wrapper around every SDK feature. Disabled
(raises ProviderError) whenever no API key is configured, so it never runs
by accident in local development.
"""

import json
import time

import httpx

from app.providers.base import Provider, ProviderError, ProviderResult

_GENERATE_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Caps a single response so cost/latency stay bounded and estimable ahead of
# a run — without this, an open-ended prompt (reasoning/coding/debugging/
# summarization) has no limit on how much a real model can generate.
#
# gemini-3.6-flash is a reasoning ("thinking") model: invisible thinking
# tokens are billed at the output rate and count against this same cap
# (confirmed 2026-09-21 — see docs/case-study/FAILURES_AND_LESSONS.md).
# At 512, most manual-category responses were dominated by thinking,
# leaving only ~16-20 tokens for the actual visible answer and truncating
# it mid-sentence. Raised to leave real headroom for both.
_MAX_OUTPUT_TOKENS = 2048


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def generate(self, model_id: str, prompt: str) -> ProviderResult:
        if not self._api_key:
            raise ProviderError("Gemini provider is not configured (missing GOOGLE_API_KEY)")

        started = time.perf_counter()
        try:
            response = httpx.post(
                _GENERATE_CONTENT_URL.format(model=model_id),
                headers={
                    "x-goog-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": _MAX_OUTPUT_TOKENS},
                },
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini request failed: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Gemini returned a non-JSON response: {exc}") from exc
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"unexpected Gemini response shape: {exc}") from exc

        usage = data.get("usageMetadata", {})
        # This is a reasoning model: invisible thinking tokens are billed at
        # the output rate and reported separately from the visible answer's
        # tokens — both must be counted, or cost is systematically
        # understated whenever thinking is used (see the cap note above).
        candidates_tokens = usage.get("candidatesTokenCount")
        thoughts_tokens = usage.get("thoughtsTokenCount")
        if candidates_tokens is None and thoughts_tokens is None:
            output_tokens = None
        else:
            output_tokens = (candidates_tokens or 0) + (thoughts_tokens or 0)

        return ProviderResult(
            text=text,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
