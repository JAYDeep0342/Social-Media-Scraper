from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_check_returns_200() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "healthy"


def test_health_check_has_request_id_header() -> None:
    response = client.get("/api/v1/health")
    assert "X-Request-ID" in response.headers
