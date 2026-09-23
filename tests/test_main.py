from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "health" in data
    assert data["health"] == "/health"
    assert "api_v1" in data


def test_favicon():
    response = client.get("/favicon.ico")
    assert response.status_code == 204


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "app_name" in data
    assert "version" in data
    assert "timestamp" in data


def test_api_v1_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data


def test_cors_headers():
    # Test request with an Origin header
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    )
    assert response.headers.get("access-control-allow-credentials") == "true"
