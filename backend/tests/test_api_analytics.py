def test_analytics_empty_state(api_client):
    response = api_client.get("/analytics")
    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 0
    assert body["escalation_rate"] is None
    assert body["avg_latency_ms"] is None
    assert body["initial_model_counts"] == {}


def test_analytics_reflects_real_routed_requests(api_client):
    # easy math -> mock-fast-v1, no escalation, validation passes
    api_client.post("/route", json={"prompt": "What is 17 * 6?"})
    # the actual V1 bug case -> escalates fast -> accurate, validation passes on final
    api_client.post("/route", json={"prompt": "What is -8 + 15?"})

    response = api_client.get("/analytics")
    assert response.status_code == 200
    body = response.json()

    assert body["total_requests"] == 2
    assert body["initial_model_counts"]["mock-fast-v1"] == 2
    assert body["final_model_counts"]["mock-fast-v1"] == 1
    assert body["final_model_counts"]["mock-accurate-v1"] == 1
    assert body["escalation_count"] == 1
    assert body["escalation_rate"] == 0.5
    assert body["validation_passed"] == 2
    assert body["avg_latency_ms"] is not None
    assert body["total_cost_usd"] is not None


def test_route_response_includes_trace_and_escalation_fields(api_client):
    response = api_client.post("/route", json={"prompt": "What is -8 + 15?"})
    assert response.status_code == 201
    body = response.json()

    assert body["initial_model_config_id"] == "mock-fast-v1"
    assert body["selected_model_config_id"] == "mock-accurate-v1"
    assert body["escalated"] is True
    assert body["attempt_count"] == 2
    assert body["validation_status"] == "passed"
    assert body["response_text"] == "7"
    assert len(body["trace_events"]) > 0
    assert body["trace_events"][0]["event_type"] == "request_received"
    event_types = [event["event_type"] for event in body["trace_events"]]
    assert "escalating" in event_types


def test_requests_list_includes_escalation_summary(api_client):
    api_client.post("/route", json={"prompt": "What is -8 + 15?"})
    response = api_client.get("/requests")
    logs = response.json()
    assert len(logs) == 1
    assert logs[0]["escalated"] is True
    assert logs[0]["initial_model_config_id"] == "mock-fast-v1"
    assert logs[0]["selected_model_config_id"] == "mock-accurate-v1"
