"""Real provider adapter: Google's Gemini API (generateContent) over plain HTTP.

Uses `httpx` directly instead of a Google SDK, matching the OpenAI adapter's
approach — a thin adapter, not a wrapper around every SDK feature. Disabled
(raises ProviderError) whenever no API key is configured, so it never runs
by accident in local development.
"""

import time

import httpx

from app.providers.base import Provider, ProviderError, ProviderResult

_GENERATE_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


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
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini request failed: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000

        data = response.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"unexpected Gemini response shape: {exc}") from exc

        usage = data.get("usageMetadata", {})
        return ProviderResult(
            text=text,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
            latency_ms=latency_ms,
        )
