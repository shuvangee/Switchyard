def test_list_experiments_empty_state(api_client):
    response = api_client.get("/experiments")
    assert response.status_code == 200
    assert response.json() == []


def test_create_experiment_with_explicit_task_ids(api_client):
    response = api_client.post(
        "/experiments",
        json={
            "task_ids": ["math-001"],
            "model_config_ids": ["mock-fast-v1", "mock-accurate-v1"],
            "name": "api test run",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["executions"]) == 2
    for execution in body["executions"]:
        assert execution["provider"] == "mock"


def test_create_experiment_by_category(api_client):
    response = api_client.post(
        "/experiments",
        json={"category": "math", "model_config_ids": ["mock-fast-v1"]},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["task_ids"]) >= 2  # math-001 and math-002


def test_create_experiment_requires_task_ids_or_category(api_client):
    response = api_client.post("/experiments", json={"model_config_ids": ["mock-fast-v1"]})
    assert response.status_code == 400


def test_create_experiment_rejects_disabled_model(api_client):
    response = api_client.post(
        "/experiments",
        json={"task_ids": ["math-001"], "model_config_ids": ["openai-gpt-4o-mini"]},
    )
    assert response.status_code == 400


def test_create_experiment_rejects_unknown_task(api_client):
    response = api_client.post(
        "/experiments",
        json={"task_ids": ["not-a-real-task"], "model_config_ids": ["mock-fast-v1"]},
    )
    assert response.status_code == 400


def test_get_experiment_detail_after_creation(api_client):
    create_response = api_client.post(
        "/experiments",
        json={"task_ids": ["math-001"], "model_config_ids": ["mock-fast-v1"]},
    )
    run_id = create_response.json()["id"]

    detail_response = api_client.get(f"/experiments/{run_id}")
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["id"] == run_id
    assert len(body["executions"]) == 1


def test_get_experiment_not_found(api_client):
    response = api_client.get("/experiments/not-a-real-run-id")
    assert response.status_code == 404


def test_list_experiments_reflects_created_runs(api_client):
    api_client.post(
        "/experiments", json={"task_ids": ["math-001"], "model_config_ids": ["mock-fast-v1"]}
    )
    response = api_client.get("/experiments")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["execution_count"] == 1
