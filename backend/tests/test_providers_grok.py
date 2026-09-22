"""Grok adapter tests. No real network calls: httpx.post is monkeypatched."""

import httpx
import pytest

from app.providers.base import ProviderError
from app.providers.grok_provider import GrokProvider


def test_raises_without_api_key():
    provider = GrokProvider(api_key=None)
    with pytest.raises(ProviderError, match="not configured"):
        provider.generate("grok-4.1-fast", "hello")


def test_normalizes_successful_response(monkeypatch):
    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "hi there"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            },
            request=request,
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GrokProvider(api_key="fake-key")
    result = provider.generate("grok-4.1-fast", "hello")

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
    provider = GrokProvider(api_key="fake-key")
    with pytest.raises(ProviderError, match="Grok request failed"):
        provider.generate("grok-4.1-fast", "hello")


def test_raises_on_malformed_response(monkeypatch):
    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"unexpected": "shape"}, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GrokProvider(api_key="fake-key")
    with pytest.raises(ProviderError, match="unexpected Grok response shape"):
        provider.generate("grok-4.1-fast", "hello")


def test_raises_on_non_json_response(monkeypatch):
    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(200, content=b"not json", request=request)

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GrokProvider(api_key="fake-key")
    with pytest.raises(ProviderError, match="Grok returned a non-JSON response"):
        provider.generate("grok-4.1-fast", "hello")
