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
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    )
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_request_id_and_process_time_headers():
    response = client.get("/")
    assert "x-request-id" in response.headers
    assert "x-process-time" in response.headers
    assert response.headers["x-process-time"].endswith("ms")


def test_custom_request_id():
    custom_id = "test-client-id-12345"
    response = client.get("/", headers={"X-Request-ID": custom_id})
    assert response.headers.get("x-request-id") == custom_id


def test_security_headers():
    response = client.get("/")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-xss-protection") == "1; mode=block"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_standardized_error_format_404():
    response = client.get("/non-existent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]
