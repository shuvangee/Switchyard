"""Real provider adapter: Groq's Chat Completions API (OpenAI-compatible).

Uses `httpx` directly, matching the OpenAI/Gemini/Grok adapters — a thin
adapter, not a wrapper around every SDK feature. Disabled (raises
ProviderError) whenever no API key is configured, so it never runs by
accident in local development.
"""

import json
import time

import httpx

from app.providers.base import Provider, ProviderError, ProviderResult

_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"

# Caps a single response so latency/TPM usage stay bounded and estimable
# ahead of a run — without this, an open-ended prompt (reasoning/coding/
# debugging/summarization) has no limit on how much a real model can
# generate, which risks blowing through the free tier's 8K-tokens/minute
# cap over a multi-task run. Matches the reasoning behind Gemini's
# _MAX_OUTPUT_TOKENS cap (see gemini_provider.py).
_MAX_TOKENS = 1024


class GroqProvider(Provider):
    name = "groq"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def generate(self, model_id: str, prompt: str) -> ProviderResult:
        if not self._api_key:
            raise ProviderError("Groq provider is not configured (missing GROQ_API_KEY)")

        started = time.perf_counter()
        try:
            response = httpx.post(
                _CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": _MAX_TOKENS,
                },
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Groq request failed: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Groq returned a non-JSON response: {exc}") from exc
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"unexpected Groq response shape: {exc}") from exc

        usage = data.get("usage", {})
        return ProviderResult(
            text=text,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
        )
