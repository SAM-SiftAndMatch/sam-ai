from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "health" in data
    assert data["health"] == "/health"


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
