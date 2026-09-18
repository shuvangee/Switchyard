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
    assert body["router_version"] == "v1"


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
