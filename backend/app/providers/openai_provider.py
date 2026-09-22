"""Real provider adapter: OpenAI's Chat Completions API over plain HTTP.

Uses `httpx` directly instead of the `openai` SDK to keep the dependency
surface small — this is a thin adapter, not a wrapper around every SDK
feature. Disabled (raises ProviderError) whenever no API key is configured,
so it never runs by accident in local development.
"""

import json
import time

import httpx

from app.providers.base import Provider, ProviderError, ProviderResult

_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def generate(self, model_id: str, prompt: str) -> ProviderResult:
        if not self._api_key:
            raise ProviderError("OpenAI provider is not configured (missing OPENAI_API_KEY)")

        started = time.perf_counter()
        try:
            response = httpx.post(
                _CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": model_id, "messages": [{"role": "user", "content": prompt}]},
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"OpenAI returned a non-JSON response: {exc}") from exc
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"unexpected OpenAI response shape: {exc}") from exc

        usage = data.get("usage", {})
        return ProviderResult(
            text=text,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
        )
