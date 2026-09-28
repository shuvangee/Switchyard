def test_route_easy_math_via_api(api_client):
    response = api_client.post("/route", json={"prompt": "What is 17 * 6?"})
    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "math"
    assert body["category_source"] == "heuristic"
    assert body["selected_model_config_id"] == "mock-fast-v1"
    assert body["status"] == "success"
    assert body["response_text"] == "102"
    assert body["rationale"] != ""
    assert body["router_version"] == "v2"


def test_route_with_explicit_category_hint(api_client):
    response = api_client.post(
        "/route", json={"prompt": "handle this", "category_hint": "coding"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "coding"
    assert body["category_source"] == "explicit"
    assert body["selected_model_config_id"] == "mock-accurate-v1"


def test_route_rejects_empty_prompt(api_client):
    response = api_client.post("/route", json={"prompt": "   "})
    assert response.status_code == 400


def test_route_with_learned_router_version(api_client):
    response = api_client.post(
        "/route", json={"prompt": "What is 17 * 6?", "router_version": "learned-v1"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["router_version"] == "learned-v1"
    assert body["selected_model_config_id"] != ""


def test_route_with_d2_baseline_router_version(api_client):
    response = api_client.post(
        "/route", json={"prompt": "Summarize this article.", "router_version": "d2-baseline"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["router_version"] == "d2-baseline"
    assert body["selected_model_config_id"] == "groq-gpt-oss-120b"
    assert body["router_score"] is None


def test_route_with_learned_v2_router_version(api_client):
    response = api_client.post(
        "/route", json={"prompt": "What is 17 * 6?", "router_version": "learned-v2"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["router_version"] == "learned-v2"
    assert body["selected_model_config_id"] in ("groq-gpt-oss-20b", "groq-gpt-oss-120b")
    assert body["router_score"] is not None


def test_route_rejects_unknown_router_version(api_client):
    response = api_client.post(
        "/route", json={"prompt": "What is 17 * 6?", "router_version": "not-a-real-version"}
    )
    assert response.status_code == 400


def test_requests_empty_state(api_client):
    response = api_client.get("/requests")
    assert response.status_code == 200
    assert response.json() == []


def test_requests_list_reflects_routed_requests(api_client):
    api_client.post("/route", json={"prompt": "What is 2 + 2?"})
    response = api_client.get("/requests")
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 1
    assert logs[0]["category"] == "math"
    assert "prompt_preview" in logs[0]


def test_request_detail_after_routing(api_client):
    create_response = api_client.post("/route", json={"prompt": "What is 9 * 9?"})
    request_id = create_response.json()["id"]

    detail_response = api_client.get(f"/requests/{request_id}")
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["id"] == request_id
    assert body["response_text"] == "81"


def test_request_detail_not_found(api_client):
    response = api_client.get("/requests/not-a-real-id")
    assert response.status_code == 404


def test_models_endpoint_includes_null_performance_before_any_run(api_client):
    response = api_client.get("/models")
    assert response.status_code == 200
    models = response.json()
    for model in models:
        assert model["performance"] is None


def test_models_endpoint_reflects_live_experiment_performance(api_client):
    api_client.post(
        "/experiments",
        json={"task_ids": ["math-001"], "model_config_ids": ["mock-fast-v1", "mock-accurate-v1"]},
    )
    response = api_client.get("/models")
    models = {m["id"]: m for m in response.json()}

    fast_perf = models["mock-fast-v1"]["performance"]
    assert fast_perf is not None
    assert fast_perf["total_executions"] == 1
    assert fast_perf["scored_executions"] == 1
    assert fast_perf["correct"] == 1

    flaky_perf = models["mock-flaky-v1"]["performance"]
    assert flaky_perf is None  # never included in that experiment run


def test_models_endpoint_includes_real_benchmark_performance_for_groq_models(api_client):
    """benchmark_performance is sourced from the committed offline
    results file, not this deployment's (empty, in these tests) DB -
    real on a fresh install, unlike `performance` above."""
    response = api_client.get("/models")
    models = {m["id"]: m for m in response.json()}

    bench = models["groq-gpt-oss-20b"]["benchmark_performance"]
    assert bench is not None
    assert bench["n_graded"] == 92
    assert 0.0 <= bench["accuracy"] <= 1.0

    assert models["mock-fast-v1"]["benchmark_performance"] is None


def test_benchmarks_coverage_endpoint(api_client):
    response = api_client.get("/benchmarks/coverage")
    assert response.status_code == 200
    body = response.json()
    assert body["total_tasks"] == 104
    assert body["auto_graded"] == 92
    assert body["manual_only"] == 12
    assert body["ungraded"] == 0
    assert len(body["by_category"]) == 8


def test_route_accepts_groq_api_key_and_never_echoes_it_back(api_client):
    response = api_client.post(
        "/route",
        json={
            "prompt": "Summarize this article.",
            "router_version": "d2-baseline",
            "groq_api_key": "a-very-secret-key-that-must-not-leak",
        },
    )
    assert response.status_code == 201
    assert "a-very-secret-key-that-must-not-leak" not in response.text
    assert "groq_api_key" not in response.json()
