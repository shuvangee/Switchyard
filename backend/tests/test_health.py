from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "switchyard"


def test_root_returns_service_info() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "switchyard-backend"
