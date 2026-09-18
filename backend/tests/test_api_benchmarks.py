def test_list_benchmarks_returns_seeded_tasks(api_client):
    response = api_client.get("/benchmarks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 8
    ids = {t["id"] for t in tasks}
    assert "math-001" in ids


def test_list_benchmarks_filters_by_category(api_client):
    response = api_client.get("/benchmarks", params={"category": "math"})
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 1
    assert all(t["category"] == "math" for t in tasks)


def test_get_benchmark_detail(api_client):
    response = api_client.get("/benchmarks/math-001")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "math-001"
    assert body["expected_output"] == "102"


def test_get_benchmark_not_found(api_client):
    response = api_client.get("/benchmarks/does-not-exist")
    assert response.status_code == 404
