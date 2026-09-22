"""Gemini adapter tests. No real network calls: httpx.post is monkeypatched."""

import httpx
import pytest

from app.providers.base import ProviderError
from app.providers.gemini_provider import GeminiProvider


def test_raises_without_api_key():
    provider = GeminiProvider(api_key=None)
    with pytest.raises(ProviderError, match="not configured"):
        provider.generate("gemini-3.6-flash", "hello")


def test_normalizes_successful_response(monkeypatch):
    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "hi there"}]}}],
                "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 3},
            },
            request=request,
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GeminiProvider(api_key="fake-key")
    result = provider.generate("gemini-3.6-flash", "hello")

    assert result.text == "hi there"
    assert result.input_tokens == 5
    assert result.output_tokens == 3
    assert result.latency_ms >= 0


def test_raises_on_http_error(monkeypatch):
    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        response = httpx.Response(401, json={"error": "unauthorized"}, request=request)
        raise httpx.HTTPStatusError("401", request=request, response=response)

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GeminiProvider(api_key="fake-key")
    with pytest.raises(ProviderError, match="Gemini request failed"):
        provider.generate("gemini-3.6-flash", "hello")


def test_raises_on_malformed_response(monkeypatch):
    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"unexpected": "shape"}, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GeminiProvider(api_key="fake-key")
    with pytest.raises(ProviderError, match="unexpected Gemini response shape"):
        provider.generate("gemini-3.6-flash", "hello")


def test_raises_on_non_json_response(monkeypatch):
    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(200, content=b"not json", request=request)

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GeminiProvider(api_key="fake-key")
    with pytest.raises(ProviderError, match="Gemini returned a non-JSON response"):
        provider.generate("gemini-3.6-flash", "hello")


def test_thinking_tokens_are_included_in_output_tokens(monkeypatch):
    """gemini-3.6-flash is a reasoning model: invisible thinking tokens are
    billed at the output rate and reported separately from the visible
    answer's tokens (thoughtsTokenCount vs candidatesTokenCount) — both
    must be counted or cost is understated whenever thinking is used.
    """

    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "hi there"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 5,
                    "candidatesTokenCount": 3,
                    "thoughtsTokenCount": 40,
                },
            },
            request=request,
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GeminiProvider(api_key="fake-key")
    result = provider.generate("gemini-3.6-flash", "hello")

    assert result.output_tokens == 43  # 3 visible + 40 thinking


def test_output_tokens_none_when_usage_metadata_missing(monkeypatch):
    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "hi there"}]}}]},
            request=request,
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GeminiProvider(api_key="fake-key")
    result = provider.generate("gemini-3.6-flash", "hello")

    assert result.output_tokens is None  # unknown, not fabricated as 0
