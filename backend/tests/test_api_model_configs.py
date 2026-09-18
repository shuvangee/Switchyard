def test_list_models_returns_mock_and_openai(api_client):
    response = api_client.get("/models")
    assert response.status_code == 200
    models = response.json()
    ids = {m["id"] for m in models}
    assert "mock-fast-v1" in ids
    assert "mock-accurate-v1" in ids
    assert "mock-flaky-v1" in ids
    assert "openai-gpt-4o-mini" in ids

    openai_model = next(m for m in models if m["id"] == "openai-gpt-4o-mini")
    assert openai_model["enabled"] is False  # no OPENAI_API_KEY in test settings
